package app.orbit.ui

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri

/** Opens a profile in its native app when installed (Instagram, X, Spotify...), else in the browser. */
fun openLink(ctx: Context, url: String) {
    val base = Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    val pkg = when {
        "instagram.com" in url -> "com.instagram.android"
        "twitter.com" in url || "x.com/" in url -> "com.twitter.android"
        "open.spotify.com" in url -> "com.spotify.music"
        "facebook.com" in url -> "com.facebook.katana"
        "youtube.com" in url -> "com.google.android.youtube"
        else -> null
    }
    if (pkg != null) {
        try { ctx.startActivity(Intent(base).setPackage(pkg)); return } catch (_: ActivityNotFoundException) { }
    }
    runCatching { ctx.startActivity(base) }
}
