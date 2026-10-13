package app.orbit.data

import android.os.SystemClock
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.serializer
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit

val AppJson = Json { ignoreUnknownKeys = true; coerceInputValues = true; isLenient = true }

object Http {
    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            chain.proceed(
                chain.request().newBuilder()
                    .header("User-Agent", "Orbit/0.1 ( https://github.com/fides402/pickflix )")
                    .build()
            )
        }
        .build()

    suspend fun get(url: String, headers: Map<String, String> = emptyMap()): Pair<Int, String> =
        withContext(Dispatchers.IO) {
            val req = Request.Builder().url(url).apply { headers.forEach { (k, v) -> header(k, v) } }.build()
            client.newCall(req).execute().use { it.code to it.body?.string().orEmpty() }
        }
}

/** MusicBrainz: open data, 1 request per second, identifies the artist. */
class MusicBrainz {
    private val gate = Mutex()
    private var last = 0L
    private val base = "https://musicbrainz.org/ws/2/"

    private suspend fun get(url: String): String = gate.withLock {
        var attempt = 0
        while (true) {
            val gap = 1100 - (SystemClock.elapsedRealtime() - last)
            if (gap > 0) delay(gap)
            val (code, body) = Http.get(url)
            last = SystemClock.elapsedRealtime()
            if (code == 200) return@withLock body
            if ((code == 503 || code == 429) && attempt++ < 3) { delay(2500L * attempt); continue }
            throw IOException("MusicBrainz $code")
        }
        @Suppress("UNREACHABLE_CODE") ""
    }

    private fun url(path: String, vararg q: Pair<String, String>): String =
        base.toHttpUrl().newBuilder().addPathSegments(path).apply {
            q.forEach { addQueryParameter(it.first, it.second) }
            addQueryParameter("fmt", "json")
        }.build().toString()

    suspend fun search(query: String): List<ArtistHit> {
        val body = get(url("artist", "query" to query, "limit" to "10"))
        return AppJson.decodeFromString(serializer<MbSearch>(), body).artists.map {
            ArtistHit(
                it.id, it.name,
                listOfNotNull(it.type, it.country, it.disambiguation?.takeIf { d -> d.isNotBlank() }).joinToString(" · "),
            )
        }
    }

    suspend fun recordings(artistId: String, offset: Int): MbRecordingPage {
        val body = get(
            url(
                "recording",
                "artist" to artistId, "inc" to "artist-credits artist-rels",
                "limit" to "100", "offset" to offset.toString(),
            )
        )
        return AppJson.decodeFromString(serializer<MbRecordingPage>(), body)
    }

    suspend fun links(artistId: String): List<Link> {
        val body = get(url("artist/$artistId", "inc" to "url-rels"))
        val rels = AppJson.decodeFromString(serializer<MbUrls>(), body).relations.mapNotNull { it.url?.resource }
        val out = mutableListOf<Link>()
        rels.firstOrNull { "instagram.com" in it }?.let { out += Link("Instagram", it) }
        rels.firstOrNull { "twitter.com" in it || "x.com/" in it }?.let { out += Link("X", it) }
        rels.firstOrNull { "open.spotify.com" in it }?.let { out += Link("Spotify", it) }
        rels.firstOrNull { "genius.com" in it }?.let { out += Link("Genius", it) }
        out += Link("MusicBrainz", "https://musicbrainz.org/artist/$artistId")
        return out
    }
}

/** Deezer public search: only used for avatars. */
class Deezer {
    suspend fun picture(name: String): String? {
        val url = "https://api.deezer.com/search/artist".toHttpUrl().newBuilder()
            .addQueryParameter("q", "\"$name\"").addQueryParameter("limit", "5").build().toString()
        val (code, body) = Http.get(url)
        if (code != 200) return null
        val hit = runCatching { AppJson.decodeFromString(serializer<DzSearch>(), body) }.getOrNull()
            ?.data?.firstOrNull { it.name.equals(name, ignoreCase = true) } ?: return null
        return hit.pic?.takeIf { "/artist//" !in it && it.isNotBlank() }
    }
}

/**
 * Genius official API (optional, needs the user's own client access token).
 * Adds producer / writer / featured / custom performance credits.
 */
class Genius(private val token: String) {
    private val h get() = mapOf("Authorization" to "Bearer $token")
    private val base = "https://api.genius.com"

    private suspend inline fun <reified T> call(path: String, vararg q: Pair<String, String>): T {
        val url = (base + path).toHttpUrl().newBuilder().apply { q.forEach { addQueryParameter(it.first, it.second) } }.build().toString()
        val (code, body) = Http.get(url, h)
        if (code == 401 || code == 403) throw IOException("Token Genius non valido")
        if (code != 200) throw IOException("Genius $code")
        return AppJson.decodeFromString(serializer<GnEnvelope<T>>(), body).response
    }

    suspend fun findArtistId(name: String): Long? {
        for (page in 1..3) {
            val r = call<GnSearch>("/search", "q" to name, "page" to page.toString(), "per_page" to "20")
            r.hits.mapNotNull { it.result.primary }.firstOrNull { it.name.equals(name, true) }?.let { return it.id }
            if (r.hits.isEmpty()) break
        }
        return null
    }

    suspend fun songIds(artistId: Long, maxSongs: Int): List<GnSongLite> {
        val out = mutableListOf<GnSongLite>()
        var page: Int? = 1
        while (page != null && out.size < maxSongs) {
            val r = call<GnSongs>("/artists/$artistId/songs", "sort" to "popularity", "per_page" to "50", "page" to page.toString())
            out += r.songs
            page = r.next
        }
        return out.take(maxSongs)
    }

    suspend fun song(id: Long): GnSong = call<GnSongFull>("/songs/$id").song
}
