package app.orbit.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.animateIntAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.ui.unit.Dp
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
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.ui.graphics.Color
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
    onGeniusSetup: () -> Unit = {},
    animateIn: Boolean = LocalMotion.current,
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
            onSelect = onSelect, animateIn = animateIn)

        Column(Modifier.fillMaxWidth().statusBarsPadding().padding(top = 18.dp)) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Micro("← Indietro", Modifier.tap(onClick = onBack)); Micro("02 / Rete")
            }
            TwoTone(
                (state?.center?.name ?: "—"), "\nnetwork",
                Modifier.padding(horizontal = 20.dp).padding(top = 12.dp, bottom = 8.dp).enter(0),
            )
            val pulse by rememberInfiniteTransition(label = "load").animateFloat(
                1f, .35f, infiniteRepeatable(tween(700), RepeatMode.Reverse), label = "pulse",
            )
            Micro(
                alpha = if (state?.loading == true) pulse else 1f,
                text = when {
                    state == null -> ""
                    state.error != null && all.isEmpty() -> state.error
                    all.isEmpty() && state.loading -> "Analisi delle registrazioni…"
                    else -> "Una rete di ${visible.size} persone" + if (state.loading) " · analisi in corso" else ""
                },
                modifier = Modifier.padding(horizontal = 20.dp),
            )
            if (state != null && !state.geniusOn) {
                Box(
                    Modifier.padding(start = 20.dp, top = 10.dp).background(P.Ink).tap(onClick = onGeniusSetup)
                        .padding(horizontal = 9.dp, vertical = 7.dp)
                ) { Micro("+ Attiva Genius per più crediti →", color = P.Paper) }
            }
            LazyRow(Modifier.padding(top = 10.dp).enter(2), contentPadding = PaddingValues(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
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
            enter = slideInVertically(spring(.82f, Spring.StiffnessMediumLow)) { it } + fadeIn(tween(200)),
            exit = slideOutVertically(tween(260)) { it } + fadeOut(tween(200)),
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
        val nodesShown by animateIntAsState(nodes, tween(600), label = "nodes")
        val scanned by animateIntAsState(state?.scanned ?: 0, tween(600), label = "scanned")
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) { Micro("Nodi", alpha = .6f); Micro("%02d".format(nodesShown)) }
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Micro("Registrazioni", alpha = .6f); Micro("$scanned / ${state?.total ?: 0}")
        }
        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Micro("Fonti", alpha = .6f)
            val g = state?.collabs?.count { Source.GENIUS in it.sources } ?: 0
            val m = state?.collabs?.count { Source.MUSICBRAINZ in it.sources } ?: 0
            Micro("MusicBrainz $m")
            if (state?.geniusOn == true) Micro(state.genius ?: "Genius $g")
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
    animateIn: Boolean,
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
            val cpop = remember { Animatable(if (animateIn) 0f else 1f) }
            LaunchedEffect(Unit) { if (animateIn) cpop.animateTo(1f, spring(.55f, Spring.StiffnessLow)) }
            Avatar(
                avatars[center.id], center.name, 76.dp,
                Modifier.align(Alignment.Center).graphicsLayer { scaleX = cpop.value; scaleY = cpop.value },
                bg = P.Ink, fg = P.Paper,
            )
            nodes.forEachIndexed { i, n ->
                key(n.id) {
                    NodeView(
                        index = i, n = n, target = pos[i],
                        d = (32f + 28f * sqrt(n.count.toFloat() / maxC)).dp,
                        sel = n.id == selectedId, avatar = avatars[n.id],
                        showLabel = i < 10 || n.id == selectedId || scale > 1.4f,
                        animateIn = animateIn, onSelect = { onSelect(n.id) },
                    )
                }
            }
        }
    }
}

/** One person: connecting line, avatar, label. Position, size and entrance are all animated. */
@Composable
private fun BoxScope.NodeView(
    index: Int, n: Collaborator, target: Offset, d: Dp, sel: Boolean,
    avatar: String?, showLabel: Boolean, animateIn: Boolean, onSelect: () -> Unit,
) {
    val pop = remember { Animatable(if (animateIn) 0f else 1f) }
    LaunchedEffect(Unit) { if (animateIn) { delay(120L + index * 20L); pop.animateTo(1f, spring(.6f, Spring.StiffnessLow)) } }
    val x by animateFloatAsState(target.x, spring(.85f, Spring.StiffnessLow), label = "x")
    val y by animateFloatAsState(target.y, spring(.85f, Spring.StiffnessLow), label = "y")
    val k by animateFloatAsState(if (sel) 1.18f else 1f, spring(.5f, Spring.StiffnessMedium), label = "sel")
    val line by animateFloatAsState(if (sel) 1f else .24f, tween(250), label = "line")

    Canvas(Modifier.fillMaxSize()) {
        val c = Offset(size.width / 2, size.height / 2)
        drawLine(
            P.Ink.copy(alpha = line), c,
            c + Offset(x.dp.toPx() * pop.value, y.dp.toPx() * pop.value),
            strokeWidth = (if (sel) 1.6f else 1f).dp.toPx(),
        )
    }
    if (sel) PulseRing(Modifier.align(Alignment.Center).offset(x.dp, y.dp), d)
    Box(
        Modifier.align(Alignment.Center).offset(x.dp, y.dp)
            .graphicsLayer { scaleX = pop.value * k; scaleY = pop.value * k; alpha = pop.value.coerceIn(0f, 1f) }
            .tap(onClick = onSelect)
    ) {
        Avatar(avatar, n.name, d, bg = if (sel) P.Ink else P.Paper, fg = if (sel) P.Paper else P.Ink)
    }
    val labelAlpha by animateFloatAsState(if (showLabel) 1f else 0f, tween(300), label = "label")
    if (labelAlpha > 0.01f) {
        Box(
            Modifier.align(Alignment.Center).offset(x.dp, y.dp + d / 2 + 9.dp)
                .graphicsLayer { alpha = labelAlpha * pop.value }
                .background(P.Paper).padding(horizontal = 5.dp, vertical = 3.dp)
        ) { Micro(n.name) }
    }
}

/** Radar-style ping around the selected person. */
@Composable
private fun PulseRing(modifier: Modifier, d: Dp) {
    val t = rememberInfiniteTransition(label = "ping")
    val p by t.animateFloat(0f, 1f, infiniteRepeatable(tween(1500, easing = LinearOutSlowInEasing)), label = "p")
    Box(
        modifier.size(d).graphicsLayer { scaleX = 1f + p * .9f; scaleY = 1f + p * .9f; alpha = (1f - p) * .5f }
            .clip(CircleShape).background(P.Ink)
    )
}

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
            if (links == null) Micro("Cerco i profili…", Modifier.padding(top = 12.dp), alpha = .5f)
            else Row(
                Modifier.padding(top = 12.dp).horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                links.forEach { l ->
                    val ig = l.label.contains("Instagram")
                    Box(
                        Modifier.background(if (ig) P.Orange else Color.Transparent)
                            .border(1.dp, if (ig) P.Orange else P.Ink)
                            .tap { openLink(ctx, l.url) }
                            .padding(horizontal = 10.dp, vertical = 9.dp)
                    ) { Micro(l.label + " ↗", color = if (ig) P.Paper else P.Ink, weight = 700) }
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                FlatButton("Esplora rete →", true, Modifier.weight(1f), onExplore)
                FlatButton(if (saved) "In lista ✓" else "Salva in lista", false, Modifier.weight(1f), onSave)
            }
        }
    }
}
