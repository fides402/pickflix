package app.orbit.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import app.orbit.data.ArtistHit

private val SUGGESTIONS = listOf("Drake", "Metro Boomin", "Dr. Dre", "Pharrell Williams", "SZA", "Quincy Jones", "Travis Scott")

@Composable
fun SearchScreen(
    query: String,
    results: List<ArtistHit>,
    searching: Boolean,
    error: String?,
    onQuery: (String) -> Unit,
    onOpen: (ArtistHit) -> Unit,
    onSuggest: (String) -> Unit,
) {
    val typing = query.isNotBlank()
    val blob by animateFloatAsState(if (typing) 0.16f else 1f, tween(500), label = "blob")
    Box(Modifier.fillMaxSize().background(P.Cream)) {
        BlobField(Modifier.fillMaxSize(), intensity = blob)
        Column(
            Modifier.fillMaxSize().statusBarsPadding().imePadding().padding(horizontal = 20.dp).padding(top = 18.dp, bottom = NavHeight + 4.dp)
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Micro("Orbit"); Micro("01 / Ricerca"); Micro("MusicBrainz")
            }
            AnimatedVisibility(
                visible = !typing,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut(tween(200)) + shrinkVertically(),
            ) {
                BasicText(
                    buildAnnotatedString {
                        append("TROVA LA TUA PROSSIMA ")
                        withStyle(SpanStyle(color = P.Orange)) { append("CONNESSIONE.") }
                    },
                    Modifier.padding(top = 14.dp).enter(0), style = T.display,
                )
            }
            Box(Modifier.weight(1f).fillMaxWidth()) {
                if (typing) {
                    LazyColumn(Modifier.fillMaxSize()) {
                        itemsIndexed(results) { i, hit ->
                            Hairline()
                            Row(
                                Modifier.fillMaxWidth().animateItem().enter(i).tap { onOpen(hit) }.padding(vertical = 12.dp),
                                verticalAlignment = Alignment.Top,
                            ) {
                                Micro("%02d".format(i + 1), Modifier.width(30.dp).padding(top = 6.dp))
                                Column(Modifier.weight(1f)) {
                                    BasicText(hit.name, style = T.h2)
                                    if (hit.detail.isNotBlank()) Micro(hit.detail, Modifier.padding(top = 5.dp), alpha = .62f)
                                }
                                Micro("→", Modifier.padding(top = 6.dp))
                            }
                        }
                        if (results.isEmpty() && !searching) item {
                            Hairline()
                            Micro(error ?: "Nessun risultato", Modifier.padding(vertical = 14.dp))
                        }
                    }
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 14.dp).enter(2), verticalAlignment = Alignment.CenterVertically) {
                BasicTextField(
                    value = query, onValueChange = onQuery,
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    textStyle = T.h1.copy(fontSize = 30.sp2),
                    cursorBrush = SolidColor(P.Orange),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(onSearch = { results.firstOrNull()?.let(onOpen) }),
                    decorationBox = { inner ->
                        if (query.isEmpty()) BasicText("Cerca un artista", style = T.h1.copy(fontSize = 30.sp2, color = P.Ink.copy(alpha = .35f)))
                        inner()
                    },
                )
                Micro(if (searching) "…" else if (typing) "${results.size} trovati" else "↵")
            }
            Box(Modifier.padding(top = 8.dp).fillMaxWidth().height(2.dp).background(P.Ink))
            LazyRow(Modifier.padding(top = 12.dp).enter(3), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                items(SUGGESTIONS) { s -> Chip(s, selected = false) { onSuggest(s) } }
            }
        }
    }
}

private val Int.sp2 get() = androidx.compose.ui.unit.TextUnit(this.toFloat(), androidx.compose.ui.unit.TextUnitType.Sp)
