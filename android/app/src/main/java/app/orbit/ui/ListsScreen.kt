package app.orbit.ui

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.orbit.data.SavedContact

@Composable
fun ListsScreen(
    items: List<SavedContact>,
    hideContacted: Boolean,
    onHide: () -> Unit,
    onContacted: (SavedContact) -> Unit,
    onRemove: (SavedContact) -> Unit,
    onExport: () -> Unit,
    geniusToken: String,
    onToken: (String) -> Unit,
    settings: Boolean = false,
    onSettings: (Boolean) -> Unit = {},
) {
    val rows = items.filter { !(hideContacted && it.contacted) }
    Box(Modifier.fillMaxSize().background(P.Olive)) {
        ConcentricRings(Modifier.fillMaxWidth().aspectRatio(1f).align(Alignment.BottomCenter).offset(y = 40.dp))
        Column(Modifier.fillMaxSize().statusBarsPadding().padding(horizontal = 20.dp).padding(top = 18.dp, bottom = NavHeight)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Micro("Orbit"); Micro(if (settings) "Chiudi impostazioni ×" else "Impostazioni", Modifier.tap { onSettings(!settings) }); Micro("03 / Liste")
            }
            AnimatedContent(
                targetState = settings,
                transitionSpec = {
                    (fadeIn(tween(380, 120)) + slideInVertically(tween(480, easing = Poster)) { it / 14 }) togetherWith
                        fadeOut(tween(160))
                },
                label = "settings",
            ) { showSettings ->
            if (showSettings) {
                Settings(geniusToken, onToken)
            } else Column {
                Row(Modifier.fillMaxWidth().padding(top = 30.dp).enter(0), verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.SpaceBetween) {
                    BasicText("le tue\nliste", style = T.display.copy(fontSize = 58.sp, lineHeight = 52.sp, letterSpacing = (-2.8).sp, color = P.Paper))
                    Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                        Micro("${items.size} contatti"); Micro("${items.count { it.contacted }} contattati"); Micro("con orbit", color = P.Forest, weight = 700)
                    }
                }
                Row(Modifier.padding(top = 16.dp, bottom = 12.dp).enter(1), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Chip(if (hideContacted) "Mostra contattati" else "Nascondi contattati", false, onClick = onHide)
                    Chip("Esporta CSV", false, onClick = onExport)
                }
                if (rows.isEmpty()) {
                    Micro("Nessun contatto. Salva qualcuno dalla rete.", Modifier.padding(top = 24.dp), color = P.Paper)
                } else LazyColumn(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    itemsIndexed(rows, key = { _, c -> c.id }) { i, c ->
                        val nameAlpha by animateFloatAsState(if (c.contacted) .45f else 1f, tween(300), label = "done")
                        Row(
                            Modifier.fillMaxWidth().animateItem().enter(i, 16.dp).background(P.Paper).padding(horizontal = 12.dp, vertical = 11.dp),
                            verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            Micro("%02d".format(i + 1), Modifier.width(22.dp))
                            Column(Modifier.weight(1f)) {
                                BasicText(c.name, style = T.h3.copy(color = P.Ink.copy(alpha = nameAlpha),
                                    textDecoration = if (c.contacted) androidx.compose.ui.text.style.TextDecoration.LineThrough else null))
                                Micro("${c.roles} · via ${c.via}", Modifier.padding(top = 5.dp), alpha = .6f)
                            }
                            Box(Modifier.size(22.dp).border(2.dp, P.Ink).tap { onContacted(c) }, contentAlignment = Alignment.Center) {
                                val mark by animateFloatAsState(if (c.contacted) 1f else 0f, spring(.45f, Spring.StiffnessMedium), label = "mark")
                                BasicText("×", Modifier.graphicsLayer { scaleX = mark; scaleY = mark; alpha = mark.coerceIn(0f, 1f) }, style = T.h3)
                            }
                            BasicText("−", Modifier.tap { onRemove(c) }.padding(horizontal = 4.dp), style = T.h3)
                        }
                    }
                }
            }
            }
        }
    }
}

@Composable
private fun Settings(token: String, onToken: (String) -> Unit) {
    var draft by remember { mutableStateOf(token) }
    Column(Modifier.padding(top = 30.dp)) {
        BasicText("impo-\nstazioni", style = T.display.copy(fontSize = 50.sp, lineHeight = 46.sp, color = P.Paper))
        Micro("Fonti dati", Modifier.padding(top = 22.dp))
        BasicText("MusicBrainz è sempre attivo e non richiede nulla. Per aggiungere i crediti di Genius (producer, writer, ruoli) incolla il tuo Client Access Token gratuito da genius.com/api-clients. Resta solo su questo telefono.", Modifier.padding(top = 8.dp), style = T.body)
        Micro("Token Genius", Modifier.padding(top = 20.dp))
        BasicTextField(
            draft, { draft = it }, Modifier.fillMaxWidth().padding(top = 6.dp).background(P.Paper).padding(12.dp),
            singleLine = true, textStyle = T.body.copy(fontSize = 15.sp), cursorBrush = SolidColor(P.Orange),
        )
        Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            FlatButton("Salva", true, Modifier.weight(1f)) { onToken(draft) }
            FlatButton("Rimuovi", false, Modifier.weight(1f)) { draft = ""; onToken("") }
        }
        Micro(if (token.isBlank()) "Genius disattivato" else "Genius attivo · le reti già caricate vengono ricalcolate", Modifier.padding(top = 10.dp), alpha = .7f)
    }
}
