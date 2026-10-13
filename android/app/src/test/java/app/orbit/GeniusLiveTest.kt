package app.orbit

import app.orbit.data.*
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Runs only when GENIUS_TOKEN is set; never stores the token. */
class GeniusLiveTest {
    @Test fun creditsAndSocials() = runBlocking {
        val token = System.getenv("GENIUS_TOKEN").orEmpty()
        assumeTrue(token.isNotBlank())
        val g = Genius(token)
        val id = g.findArtistId("Drake")
        println("LIVE artistId=$id")
        val songs = g.songIds(id!!, 8)
        println("LIVE songs=${songs.map { it.title }}")
        val agg = Aggregator(ArtistHit("x", "Drake"))
        songs.forEach { agg.addGenius(g.song(it.id)) }
        val snap = agg.snapshot()
        println("LIVE people=${snap.size}")
        snap.take(12).forEach { println("LIVE ${it.name} | ${it.roles.map { r -> r.label }} | ${it.count} brani | img=${it.image != null}") }
        val bad = snap.filter { p -> listOf("Records", "Entertainment", "Music Group", "Publishing").any { it in p.name } }
        println("LIVE companies still present=${bad.map { it.name }}")
        val a = g.artist(snap.first { it.id.startsWith("g:") }.id.removePrefix("g:").toLong())
        println("LIVE social ${a.name}: ig=${a.instagram} x=${a.twitter} fb=${a.facebook} url=${a.url}")
        val d = g.artist(id)
        println("LIVE social Drake: ig=${d.instagram} x=${d.twitter}")
    }
}

class NormNameTest {
    @Test fun nicknamesMerge() {
        check(normName("Noel “Gadget” Campbell") == normName("Noel Campbell"))
        check(normName("Boi-1da") == normName("Boi‐1da"))
    }
}
