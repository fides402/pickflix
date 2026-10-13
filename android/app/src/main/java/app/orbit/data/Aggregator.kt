package app.orbit.data

private val noise = setOf("[unknown]", "[anonymous]", "[no artist]", "various artists", "[traditional]", "[data]")
fun normName(s: String) = s.lowercase().filter { it.isLetterOrDigit() }

/** Merges credits coming from different sources into one person per name. */
class Aggregator(private val center: ArtistHit) {
    private class Acc(val id: String, val name: String, val mbId: String?) {
        val roles = linkedSetOf<Role>()
        val tracks = LinkedHashMap<String, Track>()
        val sources = linkedSetOf<Source>()
    }

    private val centerKey = normName(center.name)
    private val people = LinkedHashMap<String, Acc>()

    private fun acc(name: String, id: String, mbId: String?): Acc? {
        val key = normName(name)
        if (key.isEmpty() || key == centerKey || name.lowercase() in noise) return null
        return people.getOrPut(key) { Acc(id, name, mbId) }
    }

    private fun Acc.hit(role: Role, title: String, year: String?, src: Source) {
        roles += role; sources += src
        tracks.putIfAbsent(normName(title), Track(title, year?.take(4)?.takeIf { it.length == 4 }))
    }

    fun addMusicBrainz(recs: List<MbRecording>) {
        for (r in recs) {
            for (c in r.credit) if (c.artist.id != center.id)
                acc(c.artist.name, c.artist.id, c.artist.id)?.hit(Role.FEATURING, r.title, r.date, Source.MUSICBRAINZ)
            for (rel in r.relations) {
                val a = rel.artist ?: continue
                if (rel.targetType != "artist" || a.id == center.id) continue
                acc(a.name, a.id, a.id)?.hit(mbRole(rel.type), r.title, r.date, Source.MUSICBRAINZ)
            }
        }
    }

    fun addGenius(s: GnSong) {
        val year = s.date?.year?.toString()
        fun GnArtist.put(role: Role) = acc(name, "g:$id", null)?.hit(role, s.title, year, Source.GENIUS)
        s.producers.forEach { it.put(Role.PRODUCER) }
        s.writers.forEach { it.put(Role.WRITER) }
        s.featured.forEach { it.put(Role.FEATURING) }
        s.custom.filter { isPersonRole(it.label) }.forEach { p -> p.artists.forEach { it.put(geniusRole(p.label)) } }
    }

    fun snapshot(limit: Int = 150): List<Collaborator> = people.values
        .map { Collaborator(it.id, it.name, it.roles, it.tracks.values.toList(), it.sources, it.mbId) }
        .sortedWith(compareByDescending<Collaborator> { it.count }.thenBy { it.name })
        .take(limit)

    private fun mbRole(t: String) = when (t) {
        "producer", "executive producer", "co-producer" -> Role.PRODUCER
        "mix", "mix-DJ" -> Role.MIXING
        "recording", "engineer", "mastering", "sound", "audio", "balance" -> Role.ENGINEER
        "writer", "composer", "lyricist" -> Role.WRITER
        else -> Role.PERFORMER
    }

    /** Genius also lists labels, publishers and video crew: they are not music collaborators. */
    private fun isPersonRole(label: String): Boolean {
        val l = label.lowercase()
        return listOf("distribut", "label", "publish", "copyright", "©", "℗", "video", "artwork", "cover", "photograph", "design", "manufactur", "licens", "marketing", "a&r")
            .none { it in l }
    }

    private fun geniusRole(label: String): Role {
        val l = label.lowercase()
        return when {
            "produc" in l -> Role.PRODUCER
            "mix" in l -> Role.MIXING
            "engineer" in l || "master" in l || "record" in l -> Role.ENGINEER
            "writ" in l || "compos" in l || "lyric" in l -> Role.WRITER
            else -> Role.PERFORMER
        }
    }
}
