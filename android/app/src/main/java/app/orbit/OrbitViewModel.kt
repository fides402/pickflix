package app.orbit

import android.app.Application
import androidx.compose.runtime.*
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import app.orbit.data.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn

enum class Tab { SEARCH, NETWORK, LISTS }

class OrbitViewModel(app: Application) : AndroidViewModel(app) {
    private val mb = MusicBrainz()
    private val deezer = Deezer()
    private val dao = OrbitDb.get(app).saved()
    private val prefs = Prefs(app)

    var tab by mutableStateOf(Tab.SEARCH)

    // search
    var query by mutableStateOf("")
        private set
    var results by mutableStateOf<List<ArtistHit>>(emptyList())
        private set
    var searching by mutableStateOf(false)
        private set
    var searchError by mutableStateOf<String?>(null)
        private set
    private var searchJob: Job? = null

    fun onQuery(q: String) {
        query = q
        searchJob?.cancel()
        searchError = null
        if (q.trim().length < 2) { results = emptyList(); searching = false; return }
        searchJob = viewModelScope.launch {
            delay(450)
            searching = true
            runCatching { mb.search(q.trim()) }
                .onSuccess { results = it }
                .onFailure { if (it !is CancellationException) searchError = "Connessione non riuscita. Riprova." }
            searching = false
        }
    }

    fun openByName(name: String) {
        viewModelScope.launch {
            runCatching { mb.search(name) }.onSuccess { it.firstOrNull()?.let(::openArtist) }
        }
    }

    // network
    val trail = mutableStateListOf<ArtistHit>()
    var network by mutableStateOf<NetworkState?>(null)
        private set
    val avatars = mutableStateMapOf<String, String>()
    var roleFilter by mutableStateOf<Role?>(null)
    var selectedId by mutableStateOf<String?>(null)
    val links = mutableStateMapOf<String, List<Link>>()
    private val cache = HashMap<String, NetworkState>()
    private var netJob: Job? = null
    private var avatarJob: Job? = null

    var geniusToken by mutableStateOf(prefs.geniusToken)
        private set
    var showSettings by mutableStateOf(false)
    fun saveToken(t: String) {
        prefs.geniusToken = t; geniusToken = t.trim(); cache.clear(); links.clear()
        trail.lastOrNull()?.let { loadNetwork(it) }
    }

    fun openArtist(hit: ArtistHit) {
        trail.add(hit)
        tab = Tab.NETWORK
        loadNetwork(hit)
    }

    fun back(): Boolean {
        if (selectedId != null) { selectedId = null; return true }
        if (tab == Tab.NETWORK && trail.size > 1) {
            trail.removeAt(trail.lastIndex)
            loadNetwork(trail.last()); return true
        }
        if (tab != Tab.SEARCH) { tab = Tab.SEARCH; return true }
        return false
    }

    private fun loadNetwork(hit: ArtistHit) {
        netJob?.cancel()
        selectedId = null
        roleFilter = null
        cache[hit.id]?.let { network = it; fetchAvatars(it); return }
        val gOn = geniusToken.isNotBlank()
        network = NetworkState(hit, geniusOn = gOn, genius = if (gOn) "Genius: ricerca artista…" else null)
        netJob = viewModelScope.launch {
            val agg = Aggregator(hit)
            var offset = 0
            var total = 0
            var mbDone = false
            var mbError: String? = null
            var gDone = !gOn
            var gStatus: String? = if (gOn) "Genius: ricerca artista…" else null
            var firstAvatars = false

            fun publish() {
                val loading = !(mbDone && gDone)
                val s = NetworkState(
                    hit, agg.snapshot(), offset, total, loading,
                    error = mbError.takeIf { agg.snapshot().isEmpty() }, genius = gStatus, geniusOn = gOn,
                )
                network = s
                if (!loading) cache[hit.id] = s
                if (!firstAvatars && s.collabs.isNotEmpty()) { firstAvatars = true; fetchAvatars(s) }
            }

            try {
                coroutineScope {
                    // MusicBrainz: sequential pages (1 req/s).
                    launch {
                        try {
                            while (true) {
                                if (total > 0 && offset >= minOf(total, MAX_RECORDINGS)) break
                                val page = mb.recordings(hit.id, offset)
                                total = page.count
                                if (page.recordings.isEmpty()) break
                                agg.addMusicBrainz(page.recordings)
                                offset += page.recordings.size
                                publish()
                            }
                        } catch (e: CancellationException) { throw e }
                        catch (e: Exception) { mbError = "MusicBrainz non raggiungibile" }
                        mbDone = true; publish()
                    }
                    // Genius: official API, runs in parallel with MusicBrainz.
                    if (gOn) launch {
                        try {
                            val g = Genius(geniusToken)
                            val id = g.findArtistId(hit.name)
                            if (id == null) { gStatus = "Genius: artista non trovato" }
                            else {
                                val songs = g.songIds(id, MAX_GENIUS_SONGS)
                                var done = 0
                                val gate = kotlinx.coroutines.sync.Semaphore(4)
                                gStatus = "Genius 0/${songs.size} brani"
                                songs.map { s ->
                                    async {
                                        gate.acquire()
                                        val full = try { runCatching { g.song(s.id) }.getOrNull() } finally { gate.release() }
                                        if (full != null) agg.addGenius(full)
                                        done++
                                        gStatus = "Genius $done/${songs.size} brani"
                                        if (done % 6 == 0 || done == songs.size) publish()
                                    }
                                }.awaitAll()
                            }
                        } catch (e: CancellationException) { throw e }
                        catch (e: Exception) { gStatus = "Genius: " + (e.message ?: "errore") }
                        gDone = true; publish()
                    }
                }
                network?.let { fetchAvatars(it) }
            } catch (e: CancellationException) {
                throw e
            }
        }
    }

    private fun fetchAvatars(s: NetworkState) {
        avatarJob?.cancel()
        avatarJob = viewModelScope.launch {
            val wanted = listOf(Triple(s.center.id, s.center.name, null as String?)) +
                s.collabs.take(48).map { Triple(it.id, it.name, it.image) }
            for ((id, name, img) in wanted) {
                if (id in avatars) continue
                if (img != null) { avatars[id] = img; continue }
                runCatching { deezer.picture(name) }.getOrNull()?.let { avatars[id] = it }
                delay(110)
            }
        }
    }

    /** Social links for a person: Genius profile (Instagram, X...), MusicBrainz relations, then a fallback search. */
    fun loadLinks(c: Collaborator) {
        if (c.id in links) return
        viewModelScope.launch {
            val out = LinkedHashMap<String, Link>()
            if (geniusToken.isNotBlank()) runCatching {
                val g = Genius(geniusToken)
                val gid = if (c.id.startsWith("g:")) c.id.removePrefix("g:").toLongOrNull() else g.findArtistId(c.name)
                gid?.let { g.artist(it) }?.let { a ->
                    a.instagram?.takeIf { it.isNotBlank() }?.let { out["Instagram"] = Link("Instagram", "https://www.instagram.com/$it") }
                    a.twitter?.takeIf { it.isNotBlank() }?.let { out["X"] = Link("X", "https://x.com/$it") }
                    a.facebook?.takeIf { it.isNotBlank() }?.let { out["Facebook"] = Link("Facebook", "https://www.facebook.com/$it") }
                    a.url?.let { out["Genius"] = Link("Genius", it) }
                }
            }
            c.mbId?.let { id ->
                runCatching { mb.links(id) }.getOrNull()?.forEach { out.putIfAbsent(it.label, it) }
            }
            if ("Instagram" !in out) {
                val q = java.net.URLEncoder.encode("${c.name} instagram", "UTF-8")
                out["Instagram"] = Link("Cerca Instagram", "https://www.google.com/search?q=$q")
            }
            val order = listOf("Instagram", "Cerca Instagram", "X", "Spotify", "Facebook", "Genius", "MusicBrainz")
            links[c.id] = out.values.sortedBy { l -> order.indexOf(l.label).let { if (it < 0) 99 else it } }
        }
    }

    // lists
    val saved: StateFlow<List<SavedContact>> = dao.all().stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())
    var hideContacted by mutableStateOf(false)

    fun toggleSave(c: Collaborator, via: String, isSaved: Boolean) = viewModelScope.launch {
        if (isSaved) dao.delete(c.id)
        else dao.upsert(SavedContact(c.id, c.name, c.roles.joinToString(" · ") { it.label }, c.count, via))
    }
    fun setContacted(id: String, v: Boolean) = viewModelScope.launch { dao.setContacted(id, v) }
    fun remove(id: String) = viewModelScope.launch { dao.delete(id) }

    fun csv(): String = "nome,ruoli,brani,via,contattato\n" + saved.value.joinToString("\n") {
        listOf(it.name, it.roles, it.tracks, it.via, if (it.contacted) "si" else "no")
            .joinToString(",") { f -> "\"" + f.toString().replace("\"", "\"\"") + "\"" }
    }

    companion object {
        const val MAX_RECORDINGS = 500
        const val MAX_GENIUS_SONGS = 60
    }
}
