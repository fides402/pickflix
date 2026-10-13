package app.orbit

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import app.cash.paparazzi.DeviceConfig
import app.cash.paparazzi.Paparazzi
import app.orbit.data.*
import app.orbit.ui.*
import org.junit.Rule
import org.junit.Test

class ScreensTest {
    @get:Rule val paparazzi = Paparazzi(deviceConfig = DeviceConfig.PIXEL_5, showSystemUi = false)

    private val names = listOf("40", "Noel Cadastre", "Noel Campbell", "Boi-1da", "Greg Moffet", "Frank Dukes", "Harley Arsenault",
        "Evan Stewart", "Vinylz", "DJ Smallz", "Lil Wayne", "ScHoolboy Q", "Travis Scott", "Rihanna", "Future", "PARTYNEXTDOOR")
    private val collabs = names.mapIndexed { i, n ->
        Collaborator(
            "id$i", n, setOf(Role.entries[i % 4], Role.PRODUCER).toSet(),
            List(14 - i.coerceAtMost(12)) { Track("After Dark $it", "2018") }, setOf(Source.MUSICBRAINZ), "mb$i",
        )
    }
    private val drake = ArtistHit("d", "Drake")

    @Test fun search() = paparazzi.snapshot { Box(Modifier.fillMaxSize().grain()) {
        SearchScreen("", emptyList(), false, null, {}, {}, {})
        BottomNav(Tab.SEARCH, {}, Modifier.align(Alignment.BottomCenter)) } }

    @Test fun searchTyping() = paparazzi.snapshot { Box(Modifier.fillMaxSize().grain()) {
        SearchScreen("dra", listOf(ArtistHit("1", "Drake", "Person · CA · Canadian rapper"), ArtistHit("2", "Drake Bell", "Person · US")), false, null, {}, {}, {})
        BottomNav(Tab.SEARCH, {}, Modifier.align(Alignment.BottomCenter)) } }

    @Test fun network() = paparazzi.snapshot { Box(Modifier.fillMaxSize().grain()) {
        NetworkScreen(NetworkState(drake, collabs, 300, 2611, false), emptyMap(), null, {}, null, {}, emptyMap(), emptySet(), { _, _ -> }, {}, {}, animateIn = false)
        BottomNav(Tab.NETWORK, {}, Modifier.align(Alignment.BottomCenter)) } }

    @Test fun networkDetail() = paparazzi.snapshot { Box(Modifier.fillMaxSize().grain()) {
        NetworkScreen(NetworkState(drake, collabs, 300, 2611, false), emptyMap(), null, {}, "id2", {}, emptyMap(), emptySet(), { _, _ -> }, {}, {}, animateIn = false) } }

    @Test fun lists() = paparazzi.snapshot { Box(Modifier.fillMaxSize().grain()) {
        ListsScreen(listOf(SavedContact("a", "Boi-1da", "Producer", 9, "Drake", true), SavedContact("b", "Frank Dukes", "Producer · Performer", 5, "Drake"),
            SavedContact("c", "Vinylz", "Producer", 3, "Drake")), false, {}, {}, {}, {}, "", {})
        BottomNav(Tab.LISTS, {}, Modifier.align(Alignment.BottomCenter)) } }
}
