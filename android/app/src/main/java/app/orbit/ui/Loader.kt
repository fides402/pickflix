package app.orbit.ui

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.orbit.data.NetworkState

/** Full-screen preload: the network is built off-screen and revealed only when ready. */
@Composable
fun NetworkLoader(state: NetworkState, modifier: Modifier = Modifier) {
    val pr = state.progress
    val pct by animateIntAsState((pr.total * 100).toInt().coerceIn(0, 100), tween(600, easing = LinearOutSlowInEasing), label = "pct")
    val bar by animateFloatAsState(pr.total.coerceIn(0f, 1f), tween(650, easing = LinearOutSlowInEasing), label = "bar")
    val t = rememberInfiniteTransition(label = "loader")
    val ping by t.animateFloat(0f, 1f, infiniteRepeatable(tween(1300, easing = LinearOutSlowInEasing)), label = "ping")

    Column(modifier.padding(horizontal = 20.dp)) {
        Micro(pr.phase.let { if (it == "Pronto") "Pronto" else "Costruisco la rete · $it" })
        Row(Modifier.padding(top = 2.dp), verticalAlignment = Alignment.Bottom) {
            BasicText(
                "%d".format(pct),
                style = T.display.copy(fontSize = 132.sp, lineHeight = 120.sp, letterSpacing = (-8).sp),
            )
            BasicText("%", Modifier.padding(bottom = 18.dp, start = 4.dp), style = T.h1.copy(color = P.Paper, fontSize = 40.sp))
        }
        // bar with a traveling disc
        Box(Modifier.fillMaxWidth().padding(top = 14.dp).height(18.dp)) {
            Canvas(Modifier.fillMaxSize()) {
                val y = size.height / 2
                val r = 7.dp.toPx()
                val track = size.width - 2 * r
                drawLine(P.Ink.copy(alpha = .22f), Offset(r, y), Offset(size.width - r, y), strokeWidth = 2.dp.toPx())
                drawLine(P.Ink, Offset(r, y), Offset(r + track * bar, y), strokeWidth = 4.dp.toPx())
                val c = Offset(r + track * bar, y)
                drawCircle(P.Ink.copy(alpha = (1f - ping) * .45f), r * (1f + ping * 1.6f), c)
                drawCircle(P.Paper, r, c)
                drawCircle(P.Ink, r * .45f, c)
            }
        }
        Column(Modifier.padding(top = 18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            SourceRow("MusicBrainz", pr.mb, "${state.scanned.coerceAtMost(state.total)} / ${minOf(state.total, 500)}".takeIf { state.total > 0 } ?: "…")
            if (state.geniusOn) SourceRow("Genius", pr.genius, state.genius?.removePrefix("Genius ")?.removePrefix("Genius: ") ?: "…")
            SourceRow("Foto", pr.photos, if (pr.photos >= 1f) "pronte" else "…")
        }
        Row(Modifier.padding(top = 18.dp), verticalAlignment = Alignment.CenterVertically) {
            Micro("${state.collabs.size} persone trovate", alpha = .7f)
            Spacer(Modifier.width(12.dp))
            AnimatedContent(
                targetState = pr.latest ?: "",
                transitionSpec = { (slideInVertically { it / 2 } + fadeIn(tween(250))) togetherWith (slideOutVertically { -it / 2 } + fadeOut(tween(200))) },
                label = "latest",
            ) { name -> if (name.isNotEmpty()) Micro("↳ $name", alpha = .55f) }
        }
    }
}

@Composable
private fun SourceRow(label: String, p: Float, detail: String) {
    val v by animateFloatAsState(p.coerceIn(0f, 1f), tween(600, easing = LinearOutSlowInEasing), label = "src")
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Micro(label); Micro(detail, alpha = .7f)
        }
        Box(Modifier.fillMaxWidth().height(2.dp).background(P.Ink.copy(alpha = .2f))) {
            Box(Modifier.fillMaxWidth(v).fillMaxHeight().background(P.Ink))
        }
    }
}
