package app.orbit.ui

import android.graphics.Bitmap
import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/* ---------- text ---------- */

@Composable
fun Micro(text: String, modifier: Modifier = Modifier, color: Color = P.Ink, alpha: Float = 1f, weight: Int = 600) {
    BasicText(
        text.uppercase(),
        modifier,
        style = T.micro.copy(color = color.copy(alpha = color.alpha * alpha), fontWeight = FontWeight(weight)),
    )
}

/** Two-tone headline, as in "Never Ending / Friending". */
@Composable
fun TwoTone(first: String, second: String, modifier: Modifier = Modifier, style: androidx.compose.ui.text.TextStyle = T.title, secondColor: Color = P.Paper) {
    BasicText(
        buildAnnotatedString {
            withStyle(SpanStyle(color = P.Ink)) { append(first) }
            withStyle(SpanStyle(color = secondColor)) { append(second) }
        },
        modifier, style = style,
    )
}

/* ---------- interaction ---------- */

/** Flat press feedback: no ripple, a small scale + fade, like a printed button. */
fun Modifier.tap(enabled: Boolean = true, onClick: () -> Unit): Modifier = composed {
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    val s by animateFloatAsState(if (pressed) 0.96f else 1f, tween(90), label = "tap")
    this
        .graphicsLayer { scaleX = s; scaleY = s; alpha = if (pressed) 0.8f else 1f }
        .clickable(interactionSource = src, indication = null, enabled = enabled, onClick = onClick)
}

@Composable
fun Chip(label: String, selected: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(
        modifier
            .background(if (selected) P.Ink else Color.Transparent)
            .border(1.dp, P.Ink)
            .tap(onClick = onClick)
            .padding(horizontal = 9.dp, vertical = 7.dp)
    ) { Micro(label, color = if (selected) P.Paper else P.Ink) }
}

@Composable
fun FlatButton(label: String, fill: Boolean, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(
        modifier
            .background(if (fill) P.Ink else Color.Transparent)
            .border(2.dp, P.Ink)
            .tap(onClick = onClick)
            .padding(vertical = 14.dp),
        contentAlignment = Alignment.Center,
    ) { BasicText(label.uppercase(), style = T.micro.copy(fontSize = 11.sp, fontWeight = FontWeight.Bold, color = if (fill) P.Paper else P.Ink)) }
}

@Composable
fun Hairline(modifier: Modifier = Modifier, alpha: Float = 0.28f) {
    Box(modifier.fillMaxWidth().height(1.dp).background(P.Ink.copy(alpha = alpha)))
}

/* ---------- grain (poster paper) ---------- */

private val noise: ImageBitmap by lazy {
    val n = 160
    val bmp = Bitmap.createBitmap(n, n, Bitmap.Config.ARGB_8888)
    val rnd = java.util.Random(7)
    val px = IntArray(n * n) { val v = rnd.nextInt(256); (0xFF shl 24) or (v shl 16) or (v shl 8) or v }
    bmp.setPixels(px, 0, n, 0, 0, n, n)
    bmp.asImageBitmap()
}
private val grainBrush by lazy { ShaderBrush(ImageShader(noise, TileMode.Repeated, TileMode.Repeated)) }

fun Modifier.grain(alpha: Float = 0.085f): Modifier = drawWithContent {
    drawContent()
    drawRect(grainBrush, alpha = alpha)
}

/* ---------- poster 1: blurred blobs ---------- */

@Composable
fun BlobField(modifier: Modifier = Modifier, intensity: Float = 1f) {
    val t = rememberInfiniteTransition(label = "blob")
    val a by t.animateFloat(0f, (2 * PI).toFloat(), infiniteRepeatable(tween(22000, easing = LinearEasing)), label = "a")
    Canvas(modifier) {
        val m = min(size.width, size.height)
        fun blob(cx: Float, cy: Float, r: Float, ph: Float) {
            val c = Offset(cx * size.width + sin(a + ph) * m * .025f, cy * size.height + cos(a * .8f + ph) * m * .03f)
            val rr = r * m
            drawCircle(
                Brush.radialGradient(
                    colorStops = arrayOf(0f to P.Orange, .36f to P.Orange, .6f to P.Amber, 1f to P.Amber.copy(alpha = 0f)),
                    center = c, radius = rr,
                ),
                radius = rr, center = c, alpha = intensity,
            )
        }
        blob(.38f, .46f, .50f, 0f)
        blob(.84f, .27f, .30f, 1.7f)
        blob(.78f, .70f, .34f, 3.1f)
        blob(.16f, .86f, .26f, 4.6f)
    }
}

/* ---------- poster 2: tangent circles ---------- */

@Composable
fun TangentRings(modifier: Modifier = Modifier, shift: Offset = Offset.Zero) {
    val t = rememberInfiniteTransition(label = "tan")
    val b by t.animateFloat(-1f, 1f, infiniteRepeatable(tween(9000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "b")
    val cols = remember {
        listOf(0xFFF5A02B, 0xFFF28E22, 0xFFEE7A1B, 0xFFE96514, 0xFFE4510C, 0xFFDE3F05, 0xFFD23702).map { Color(it) }
    }
    Canvas(modifier) {
        drawRect(P.Yellow)
        val tp = Offset(size.width * .80f, size.height * .60f) + shift
        val ang = Math.toRadians(-110.0 + b * 4)
        val dir = Offset(cos(ang).toFloat(), sin(ang).toFloat())
        var r = size.width * .93f
        for (c in cols) { drawCircle(c, r, tp + dir * r); r *= .74f }
    }
}

/* ---------- poster 3: concentric rings ---------- */

@Composable
fun ConcentricRings(modifier: Modifier = Modifier) {
    val cols = remember {
        listOf(0xFF5F8227, 0xFF43721F, 0xFF2D5C1C, 0xFF1D4D18, 0xFF134013, 0xFF0B3010, 0xFF06200A, 0xFF021005, 0xFF000000).map { Color(it) }
    }
    Canvas(modifier) {
        var r = size.width * .52f
        cols.forEachIndexed { i, c ->
            drawCircle(c, r, Offset(size.width / 2f + i * 1.5f, size.height * .5f + i * 2f))
            r *= .82f
        }
    }
}

/* ---------- avatars ---------- */

fun initials(name: String): String =
    name.replace(Regex("[^\\p{L}\\p{N} ]"), " ").trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.take(2)
        .joinToString("") { it.first().uppercase() }

/** Cream disc without outline. Photo (when found) is printed in black and white. */
@Composable
fun Avatar(url: String?, name: String, size: Dp, modifier: Modifier = Modifier, bg: Color = P.Paper, fg: Color = P.Ink) {
    Box(modifier.size(size).clip(CircleShape).background(bg), contentAlignment = Alignment.Center) {
        BasicText(initials(name), style = T.micro.copy(fontSize = (size.value * .3f).sp, fontWeight = FontWeight.ExtraBold, color = fg, letterSpacing = (-0.3).sp))
        if (url != null) {
            AsyncImage(
                model = url, contentDescription = name, contentScale = ContentScale.Crop,
                colorFilter = ColorFilter.colorMatrix(ColorMatrix().apply { setToSaturation(0f) }),
                modifier = Modifier.fillMaxSize(),
            )
        }
    }
}
