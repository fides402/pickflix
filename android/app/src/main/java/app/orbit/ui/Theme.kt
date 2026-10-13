package app.orbit.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import app.orbit.R

/** Palette taken from the three reference posters. */
object P {
    val Cream = Color(0xFFF3EDDD)
    val Paper = Color(0xFFF8F4E8)
    val Ink = Color(0xFF141311)
    val Orange = Color(0xFFF0501E)
    val Amber = Color(0xFFF5A02B)
    val Yellow = Color(0xFFF7B042)
    val Vermilion = Color(0xFFDE3F05)
    val Olive = Color(0xFFA4B32A)
    val Forest = Color(0xFF0F4D1A)
}

@OptIn(ExperimentalTextApi::class)
private fun grot(w: Int) = Font(R.font.intertight, FontWeight(w), variationSettings = FontVariation.Settings(FontVariation.weight(w)))

val Grotesk = FontFamily(grot(400), grot(500), grot(600), grot(700), grot(800))

object T {
    private val base = TextStyle(fontFamily = Grotesk, color = P.Ink)
    val display = base.copy(fontWeight = FontWeight.Bold, fontSize = 49.sp, lineHeight = 45.sp, letterSpacing = (-2.3).sp)
    val title = base.copy(fontWeight = FontWeight.Bold, fontSize = 44.sp, lineHeight = 41.sp, letterSpacing = (-2).sp)
    val h1 = base.copy(fontWeight = FontWeight.Bold, fontSize = 34.sp, lineHeight = 32.sp, letterSpacing = (-1.5).sp)
    val h2 = base.copy(fontWeight = FontWeight.Bold, fontSize = 24.sp, lineHeight = 24.sp, letterSpacing = (-0.9).sp)
    val h3 = base.copy(fontWeight = FontWeight.Bold, fontSize = 20.sp, lineHeight = 21.sp, letterSpacing = (-0.7).sp)
    val body = base.copy(fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 18.sp, letterSpacing = (-0.15).sp)
    val micro = base.copy(fontWeight = FontWeight.SemiBold, fontSize = 10.sp, lineHeight = 12.sp, letterSpacing = 0.9.sp)
}
