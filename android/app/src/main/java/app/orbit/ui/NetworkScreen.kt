package app.orbit.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.orbit.data.*
import kotlinx.coroutines.delay
import kotlin.math.cos
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

@Composable
fun NetworkScreen(
    state: NetworkState?,
    avatars: Map<String, String>,
    filter: Role?,
    onFilter: (Role?) -> Unit,
    selectedId: String?,
    onSelect: (String?) -> Unit,
    links: Map<String, List<Link>>,
    savedIds: Set<String>,
    onSave: (Collaborator, Boolean) -> Unit,
    onExplore: (Collaborator) -> Unit,
    onBack: () -> Unit,
) {
    var pan by remember { mutableStateOf(Offset.Zero) }
    var scale by remember { mutableFloatStateOf(.82f) }
    val all = state?.collabs.orEmpty()
    val visible = remember(all, filter) { all.filter { filter == null || filter in it.roles }.take(60) }
    val selected = visible.firstOrNull { it.id == selectedId }

    Box(Modifier.fillMaxSize()) {
        TangentRings(Modifier.fillMaxSize(), shift = Offset(pan.x * .06f, pan.y * .06f))

        if (state != null) GraphLayer(state.center, visible, avatars, selected?.id, scale, pan,
            onTransform = { p, z -> pan += p; scale = (scale * z).coerceIn(.45f, 3f) },
            onSelect = onSelect)

        Column(Modifier.fillMaxWidth().statusBarsPadding().padding(top = 18.dp)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Micro("← Indietro", Modifier.tap(onClick = onBack)); Micro("02 / Rete")
            }
            TwoTone(
                (state?.center?.name ?: "—"), "\nnetwork",
                Modifier.padding(horizontal = 20.dp).padding(top = 12.dp, bottom = 8.dp),
            )
            Micro(
                when {
                    state == null -> ""
                    state.error != null && all.isEmpty() -> state.error
                    all.isEmpty() && state.loading -> "Analisi delle registrazioni…"
                    else -> "Una rete di ${visible.size} persone" + if (state.loading) " · analisi in corso" else ""
                },
                Modifier.padding(horizontal = 20.dp),
            )
            LazyRow(Modifier.padding(top = 10.dp), contentPadding = PaddingValues(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                item { Chip("Tutti ${all.size}", filter == null) { onFilter(null) } }
                items(Role.entries.filter { r -> all.any { r in it.roles } }) { r ->
                    Chip("${r.label} ${all.count { r in it.roles }}", filter == r) { onFilter(r) }
                }
            }
        }

        Column(
            Modifier.align(Alignment.CenterEnd).padding(end = 16.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            ZoomBtn("+") { scale = (scale * 1.25f).coerceIn(.45f, 3f) }
            ZoomBtn("−") { scale = (scale / 1.25f).coerceIn(.45f, 3f) }
        }

        Footer(state, visible.size, Modifier.align(Alignment.BottomStart).padding(bottom = NavHeight + 4.dp))

        AnimatedVisibility(
            visible = selected != null,
            modifier = Modifier.align(Alignment.BottomCenter),
            enter = slideInVertically { it }, exit = slideOutVertically { it },
        ) {
            if (selected != null) DetailPanel(
                c = selected, index = visible.indexOf(selected) + 1, total = visible.size,
                centerName = state?.center?.name.orEmpty(),
                links = links[selected.id], saved = selected.id in savedIds,
                onClose = { onSelect(null) }, onSave = { onSave(selected, selected.id in savedIds) },
                onExplore = { onExplore(selected) },
            )
        }
    }
}

@Composable
private fun ZoomBtn(label: String, onClick: () -> Unit) {
    Box(Modifier.size(34.dp).border(1.dp, P.Ink).tap(onClick = onClick), contentAlignment = Alignment.Center) {
        BasicText(label, style = T.h3)
    }
}

@Composable
private fun Footer(state: NetworkState?, nodes: Int, modifier: Modifier) {
    Row(modifier.fillMaxWidth().padding(end = 20.dp), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(20.dp)) {
        Box(Modifier.size(12.dp, 30.dp).background(P.Ink))
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) { Micro("Nodi", alpha = .6f); Micro("%02d".format(nodes)) }
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Micro("Registrazioni", alpha = .6f); Micro("${state?.scanned ?: 0} / ${state?.total ?: 0}")
        }
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Micro("Fonti", alpha = .6f)
            Micro(buildList {
                add("MusicBrainz")
                if (state?.collabs?.any { Source.GENIUS in it.sources } == true) add("Genius")
            }.joinToString(" + "))
        }
    }
}

@Composable
private fun GraphLayer(
    center: ArtistHit,
    nodes: List<Collaborator>,
    avatars: Map<String, String>,
    selectedId: String?,
    scale: Float,
    pan: Offset,
    onTransform: (Offset, Float) -> Unit,
    onSelect: (String?) -> Unit,
) {
    val maxC = (nodes.maxOfOrNull { it.count } ?: 1).coerceAtLeast(1)
    val pos = remember(nodes) {
        nodes.mapIndexed { i, _ ->
            val r = 96f + 44f * sqrt(i.toFloat()); val a = i * 2.3999632f
            Offset(r * cos(a), r * sin(a))
        }
    }
    Box(
        Modifier.fillMaxSize()
            .pointerInput(Unit) { detectTransformGestures { _, p, z, _ -> onTransform(p, z) } }
            .pointerInput(Unit) { detectTapGestures { onSelect(null) } }
    ) {
        Box(
            Modifier.fillMaxSize().graphicsLayer {
                scaleX = scale; scaleY = scale; translationX = pan.x; translationY = pan.y + size.height * .04f
            }
        ) {
            Canvas(Modifier.fillMaxSize()) {
                val c = Offset(size.width / 2, size.height / 2)
                nodes.forEachIndexed { i, n ->
                    val sel = n.id == selectedId
                    drawLine(
                        P.Ink.copy(alpha = if (sel) 1f else .24f), c,
                        c + Offset(pos[i].x.dp.toPx(), pos[i].y.dp.toPx()),
                        strokeWidth = (if (sel) 1.6f else 1f).dp.toPx(),
                    )
                }
            }
            // center
            Avatar(avatars[center.id], center.name, 76.dp, Modifier.align(Alignment.Center), bg = P.Ink, fg = P.Paper)
            nodes.forEachIndexed { i, n ->
                key(n.id) {
                    val d = (32f + 28f * sqrt(n.count.toFloat() / maxC)).dp
                    val sel = n.id == selectedId
                    val pop = remember { Animatable(0f) }
                    LaunchedEffect(Unit) { delay(i * 18L); pop.animateTo(1f, spring(.6f, Spring.StiffnessLow)) }
                    val k by animateScale(sel)
                    Box(
                        Modifier.align(Alignment.Center).offset(pos[i].x.dp, pos[i].y.dp)
                            .graphicsLayer { scaleX = pop.value * k; scaleY = pop.value * k; alpha = pop.value.coerceIn(0f, 1f) }
                            .tap { onSelect(n.id) }
                    ) {
                        Avatar(
                            avatars[n.id], n.name, d,
                            bg = if (sel) P.Ink else P.Paper, fg = if (sel) P.Paper else P.Ink,
                        )
                    }
                    if (i < 10 || sel || scale > 1.4f) {
                        Box(
                            Modifier.align(Alignment.Center)
                                .offset(pos[i].x.dp, pos[i].y.dp + d / 2 + 9.dp)
                                .background(P.Paper).padding(horizontal = 5.dp, vertical = 3.dp)
                        ) { Micro(n.name, weight = 600) }
                    }
                }
            }
        }
    }
}

@Composable
private fun animateScale(sel: Boolean) =
    androidx.compose.animation.core.animateFloatAsState(if (sel) 1.18f else 1f, spring(.5f, Spring.StiffnessMedium), label = "sel")

@Composable
private fun DetailPanel(
    c: Collaborator, index: Int, total: Int, centerName: String,
    links: List<Link>?, saved: Boolean,
    onClose: () -> Unit, onSave: () -> Unit, onExplore: () -> Unit,
) {
    val ctx = LocalContext.current
    Column(
        Modifier.fillMaxWidth().heightIn(max = 560.dp).background(P.Paper)
            .navigationBarsPadding()
    ) {
        Box(Modifier.fillMaxWidth().height(3.dp).background(P.Ink))
        Column(Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Micro("%02d / %02d".format(index, total)); Micro("Chiudi ×", Modifier.tap(onClick = onClose))
            }
            BasicText(c.name, Modifier.padding(top = 10.dp, bottom = 10.dp), style = T.h1.copy(fontSize = 38.sp, lineHeight = 36.sp))
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                c.roles.forEach { r ->
                    Box(
                        Modifier.then(if (r == Role.PRODUCER) Modifier.background(P.Orange) else Modifier.border(1.dp, P.Ink))
                            .padding(horizontal = 6.dp, vertical = 4.dp)
                    ) { Micro(r.label, color = if (r == Role.PRODUCER) P.Paper else P.Ink) }
                }
            }
            Micro("${c.count} brani con $centerName", Modifier.padding(top = 14.dp))
            Micro("Fonti ${c.sources.joinToString(" + ") { it.label }}", Modifier.padding(top = 4.dp), alpha = .55f)
            Column(Modifier.padding(top = 12.dp)) {
                c.tracks.take(5).forEach { t ->
                    Hairline(alpha = .2f)
                    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        BasicText(t.title, Modifier.weight(1f), style = T.body)
                        Micro(t.year ?: "—")
                    }
                }
            }
            Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                (links ?: c.mbId?.let { listOf(Link("MusicBrainz", "https://musicbrainz.org/artist/$it")) }.orEmpty()).forEach { l ->
                    Micro(l.label, Modifier.tap {
                        runCatching { ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(l.url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
                    })
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                FlatButton("Esplora rete →", true, Modifier.weight(1f), onExplore)
                FlatButton(if (saved) "In lista ✓" else "Salva in lista", false, Modifier.weight(1f), onSave)
            }
        }
    }
}
