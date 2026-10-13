package app.orbit.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

enum class Role(val label: String) {
    PRODUCER("Producer"), MIXING("Mixing"), ENGINEER("Engineer"), FEATURING("Featuring"), WRITER("Writer"), PERFORMER("Performer")
}

enum class Source(val label: String) { MUSICBRAINZ("MusicBrainz"), GENIUS("Genius") }

data class ArtistHit(
    val id: String,
    val name: String,
    val detail: String = "",
)

data class Track(val title: String, val year: String?)

data class Collaborator(
    val id: String,
    val name: String,
    val roles: Set<Role>,
    val tracks: List<Track>,
    val sources: Set<Source>,
    val mbId: String? = null,
) {
    val count: Int get() = tracks.size
}

data class NetworkState(
    val center: ArtistHit,
    val collabs: List<Collaborator> = emptyList(),
    val scanned: Int = 0,
    val total: Int = 0,
    val loading: Boolean = true,
    val note: String? = null,
    val error: String? = null,
)

data class Link(val label: String, val url: String)

/* ---- MusicBrainz JSON ---- */
@Serializable data class MbSearch(val artists: List<MbArtist> = emptyList())
@Serializable data class MbArtist(
    val id: String,
    val name: String,
    val type: String? = null,
    val country: String? = null,
    val disambiguation: String? = null,
)
@Serializable data class MbRecordingPage(
    @SerialName("recording-count") val count: Int = 0,
    val recordings: List<MbRecording> = emptyList(),
)
@Serializable data class MbRecording(
    val id: String,
    val title: String = "",
    @SerialName("first-release-date") val date: String? = null,
    @SerialName("artist-credit") val credit: List<MbCredit> = emptyList(),
    val relations: List<MbRel> = emptyList(),
)
@Serializable data class MbCredit(val artist: MbRef)
@Serializable data class MbRef(val id: String, val name: String)
@Serializable data class MbRel(
    val type: String = "",
    @SerialName("target-type") val targetType: String = "",
    val artist: MbRef? = null,
)
@Serializable data class MbUrls(val relations: List<MbUrlRel> = emptyList())
@Serializable data class MbUrlRel(val type: String = "", val url: MbUrl? = null)
@Serializable data class MbUrl(val resource: String = "")

/* ---- Deezer ---- */
@Serializable data class DzSearch(val data: List<DzArtist> = emptyList())
@Serializable data class DzArtist(val name: String = "", @SerialName("picture_medium") val pic: String? = null)

/* ---- Genius ---- */
@Serializable data class GnEnvelope<T>(val response: T)
@Serializable data class GnSearch(val hits: List<GnHit> = emptyList())
@Serializable data class GnHit(val result: GnSongLite)
@Serializable data class GnSongLite(
    val id: Long = 0,
    val title: String = "",
    @SerialName("primary_artist") val primary: GnArtist? = null,
)
@Serializable data class GnArtist(val id: Long = 0, val name: String = "")
@Serializable data class GnSongs(val songs: List<GnSongLite> = emptyList(), @SerialName("next_page") val next: Int? = null)
@Serializable data class GnSongFull(val song: GnSong)
@Serializable data class GnSong(
    val id: Long = 0,
    val title: String = "",
    @SerialName("release_date_components") val date: GnDate? = null,
    @SerialName("primary_artist") val primary: GnArtist? = null,
    @SerialName("featured_artists") val featured: List<GnArtist> = emptyList(),
    @SerialName("producer_artists") val producers: List<GnArtist> = emptyList(),
    @SerialName("writer_artists") val writers: List<GnArtist> = emptyList(),
    @SerialName("custom_performances") val custom: List<GnPerf> = emptyList(),
)
@Serializable data class GnDate(val year: Int? = null)
@Serializable data class GnPerf(val label: String = "", val artists: List<GnArtist> = emptyList())
