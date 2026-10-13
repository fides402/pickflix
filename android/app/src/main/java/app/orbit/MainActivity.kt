package app.orbit

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.ui.graphics.TransformOrigin
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import app.orbit.data.ArtistHit
import app.orbit.ui.*
import androidx.compose.animation.core.CubicBezierEasing

class MainActivity : ComponentActivity() {
    private val vm: OrbitViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.light(Color.TRANSPARENT, Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.light(Color.TRANSPARENT, Color.TRANSPARENT),
        )
        setContent { OrbitApp(vm) }
    }
}

@Composable
fun OrbitApp(vm: OrbitViewModel) {
    val ctx = LocalContext.current
    val saved by vm.saved.collectAsState()
    val savedIds = remember(saved) { saved.map { it.id }.toSet() }
    BackHandler(enabled = vm.selectedId != null || vm.tab != Tab.SEARCH) { vm.back() }

    Box(Modifier.fillMaxSize().grain()) {
        val zc = remember { intArrayOf(0) }
        AnimatedContent(
            targetState = vm.tab,
            transitionSpec = {
                zc[0] += 1
                (EnterTransition.None togetherWith
                    scaleOut(tween(760, easing = Poster), targetScale = .94f, transformOrigin = TransformOrigin(.5f, 1f)))
                    .apply { targetContentZIndex = zc[0].toFloat() }
            },
            label = "tab",
        ) { tab ->
            val reveal by transition.animateFloat(
                transitionSpec = { tween(760, easing = CubicBezierEasing(.65f, 0f, .2f, 1f)) }, label = "reveal",
            ) { if (it == EnterExitState.PreEnter) 0f else 1f }
            Box(Modifier.fillMaxSize().irisReveal(reveal, (tab.ordinal + .5f) / 3f)) {
                when (tab) {
                Tab.SEARCH -> SearchScreen(
                vm.query, vm.results, vm.searching, vm.searchError,
                onQuery = vm::onQuery, onOpen = vm::openArtist, onSuggest = vm::openByName,
            )
            Tab.NETWORK -> NetworkScreen(
                state = vm.network, avatars = vm.avatars,
                filter = vm.roleFilter, onFilter = { vm.roleFilter = it; vm.selectedId = null },
                selectedId = vm.selectedId,
                onSelect = { id ->
                    vm.selectedId = id
                    vm.network?.collabs?.firstOrNull { it.id == id }?.let(vm::loadLinks)
                },
                links = vm.links, savedIds = savedIds,
                onSave = { c, isSaved -> vm.toggleSave(c, vm.network?.center?.name.orEmpty(), isSaved) },
                onExplore = { c ->
                    val mb = c.mbId
                    if (mb != null) vm.openArtist(ArtistHit(mb, c.name))
                    else vm.openByName(c.name)
                },
                onBack = { vm.back() },
                onGeniusSetup = { vm.showSettings = true; vm.tab = Tab.LISTS },
            )
            Tab.LISTS -> ListsScreen(
                items = saved, hideContacted = vm.hideContacted, onHide = { vm.hideContacted = !vm.hideContacted },
                onContacted = { vm.setContacted(it.id, !it.contacted) }, onRemove = { vm.remove(it.id) },
                onExport = {
                    ctx.startActivity(
                        Intent.createChooser(
                            Intent(Intent.ACTION_SEND).setType("text/csv").putExtra(Intent.EXTRA_TEXT, vm.csv()), "Esporta lista",
                        )
                    )
                },
                geniusToken = vm.geniusToken, onToken = vm::saveToken,
                settings = vm.showSettings, onSettings = { vm.showSettings = it },
            )
                }
            }
        }
        AnimatedVisibility(
            visible = vm.selectedId == null,
            modifier = Modifier.align(Alignment.BottomCenter),
            enter = slideInVertically(tween(350, easing = Poster)) { it } + fadeIn(tween(250)),
            exit = slideOutVertically(tween(250)) { it } + fadeOut(tween(200)),
        ) { BottomNav(vm.tab, { vm.tab = it }) }
    }
}
