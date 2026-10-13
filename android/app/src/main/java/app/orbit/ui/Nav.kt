package app.orbit.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import app.orbit.Tab

val NavHeight: Dp = 56.dp

@Composable
fun BottomNav(tab: Tab, onTab: (Tab) -> Unit, modifier: Modifier = Modifier) {
    val bg by animateColorAsState(
        when (tab) { Tab.SEARCH -> P.Cream; Tab.NETWORK -> Color(0xFFEE9A2A); Tab.LISTS -> P.Olive }, label = "navbg",
    )
    Column(modifier.fillMaxWidth().background(bg).navigationBarsPadding()) {
        Hairline()
        Row(Modifier.fillMaxWidth().height(NavHeight - 1.dp)) {
            listOf(Tab.SEARCH to "Cerca", Tab.NETWORK to "Rete", Tab.LISTS to "Liste").forEach { (t, label) ->
                val on = t == tab
                val s by animateFloatAsState(if (on) 1f else 0f, spring(.5f, Spring.StiffnessMedium), label = "dot")
                Row(
                    Modifier.weight(1f).fillMaxHeight().tap { onTab(t) },
                    verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center,
                ) {
                    Box(Modifier.size(8.dp).scale(s).clip(CircleShape).background(P.Ink))
                    Spacer(Modifier.width(7.dp))
                    Micro(label, alpha = if (on) 1f else .55f)
                }
            }
        }
    }
}
