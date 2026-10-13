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
    fun saveToken(t: String) { prefs.geniusToken = t; geniusToken = t.trim(); cache.clear() }

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
        network = NetworkState(hit)
        netJob = viewModelScope.launch {
            val agg = Aggregator(hit)
            var offset = 0
            var total = 0
            var note: String? = null
            try {
                while (true) {
                    if (total > 0 && offset >= minOf(total, MAX_RECORDINGS)) break
                    val page = mb.recordings(hit.id, offset)
                    total = page.count
                    if (page.recordings.isEmpty()) break
                    agg.addMusicBrainz(page.recordings)
                    offset += page.recordings.size
                    network = NetworkState(hit, agg.snapshot(), offset, total, loading = true)
                    if (offset == page.recordings.size) fetchAvatars(network!!)
                }
                if (geniusToken.isNotBlank()) {
                    note = runCatching { addGenius(hit, agg) { network = NetworkState(hit, agg.snapshot(), offset, total, true) } }
                        .exceptionOrNull()?.message
                }
                val done = NetworkState(hit, agg.snapshot(), offset, total, loading = false, note = note)
                network = done
                cache[hit.id] = done
                fetchAvatars(done)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                val cur = network
                network = (cur ?: NetworkState(hit)).copy(loading = false, error = e.message ?: "Errore di rete")
            }
        }
    }

    private suspend fun addGenius(hit: ArtistHit, agg: Aggregator, tick: () -> Unit) = coroutineScope {
        val g = Genius(geniusToken)
        val id = g.findArtistId(hit.name) ?: return@coroutineScope
        val songs = g.songIds(id, MAX_GENIUS_SONGS)
        val gate = kotlinx.coroutines.sync.Semaphore(4)
        songs.map { s ->
            async {
                gate.acquire()
                try { runCatching { g.song(s.id) }.getOrNull() } finally { gate.release() }
            }
        }.awaitAll().filterNotNull().forEach { agg.addGenius(it) }
        tick()
    }

    private fun fetchAvatars(s: NetworkState) {
        avatarJob?.cancel()
        avatarJob = viewModelScope.launch {
            val wanted = listOf(s.center.id to s.center.name) + s.collabs.take(48).map { it.id to it.name }
            for ((id, name) in wanted) {
                if (id in avatars) continue
                runCatching { deezer.picture(name) }.getOrNull()?.let { avatars[id] = it }
                delay(110)
            }
        }
    }

    fun loadLinks(c: Collaborator) {
        val mbId = c.mbId ?: return
        if (c.id in links) return
        viewModelScope.launch {
            links[c.id] = runCatching { mb.links(mbId) }.getOrDefault(listOf(Link("MusicBrainz", "https://musicbrainz.org/artist/$mbId")))
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
