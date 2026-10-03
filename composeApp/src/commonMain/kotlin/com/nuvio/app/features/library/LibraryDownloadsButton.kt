package com.nuvio.app.features.library

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Download
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.CompositingStrategy
import androidx.compose.ui.graphics.TileMode
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nuvio.app.core.ui.accentBrush
import com.nuvio.app.core.ui.gradientMask
import com.nuvio.app.core.ui.nuvio
import com.nuvio.app.core.ui.themePalette
import com.nuvio.app.features.downloads.DownloadStatus
import com.nuvio.app.features.downloads.DownloadsRepository
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.compose_settings_root_downloads_title
import nuvio.composeapp.generated.resources.downloads_live_completed
import nuvio.composeapp.generated.resources.downloads_status_downloading
import nuvio.composeapp.generated.resources.downloads_status_failed
import nuvio.composeapp.generated.resources.downloads_status_paused
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun LibraryDownloadsButton(onClick: () -> Unit) {
    val downloads by remember {
        DownloadsRepository.ensureLoaded()
        DownloadsRepository.uiState
    }.collectAsStateWithLifecycle()
    val hasUnseenCompleted by DownloadsRepository.hasUnseenCompleted.collectAsStateWithLifecycle()

    val activeCount = downloads.items.count {
        it.status == DownloadStatus.Downloading || it.status == DownloadStatus.Paused
    }
    val hasFailed = downloads.items.any { it.status == DownloadStatus.Failed }
    val hasDownloading = downloads.items.any { it.status == DownloadStatus.Downloading }
    val statusDescription = when {
        hasDownloading -> stringResource(Res.string.downloads_status_downloading, activeCount.toString())
        activeCount > 0 -> stringResource(Res.string.downloads_status_paused, activeCount.toString())
        hasFailed -> stringResource(Res.string.downloads_status_failed)
        hasUnseenCompleted -> stringResource(Res.string.downloads_live_completed)
        else -> ""
    }

    TextButton(
        onClick = onClick,
        modifier = Modifier.semantics { stateDescription = statusDescription },
    ) {
        BadgedBox(
            badge = {
                when {
                    activeCount > 0 -> Badge {
                        Text(if (activeCount > 99) "99+" else activeCount.toString())
                    }
                    hasFailed -> Badge { Text("!") }
                    hasUnseenCompleted -> Badge()
                }
            },
        ) {
            when {
                hasDownloading -> FlowingDownloadIcon()
                hasUnseenCompleted -> DownloadIcon(
                    modifier = Modifier.gradientMask(MaterialTheme.themePalette.accentBrush()),
                    tint = Color.White,
                )
                else -> DownloadIcon(tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.width(12.dp))
        Text(
            text = stringResource(Res.string.compose_settings_root_downloads_title),
            modifier = Modifier.widthIn(max = 84.dp),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun FlowingDownloadIcon() {
    val palette = MaterialTheme.themePalette
    val dimAlpha = MaterialTheme.nuvio.opacity.overlayLight
    val colors = palette.accentGradient.takeIf { it.size >= 2 }
        ?: listOf(palette.secondary, palette.secondary.copy(alpha = dimAlpha))
    val phase by rememberInfiniteTransition(label = "downloadsFlow").animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(durationMillis = 1600, easing = LinearEasing)),
        label = "downloadsFlowPhase",
    )
    DownloadIcon(
        modifier = Modifier
            .graphicsLayer { compositingStrategy = CompositingStrategy.Offscreen }
            .drawWithContent {
                drawContent()
                val offset = phase * size.height * 2f
                drawRect(
                    brush = Brush.linearGradient(
                        colors = colors,
                        start = Offset(0f, offset),
                        end = Offset(0f, offset + size.height),
                        tileMode = TileMode.Mirror,
                    ),
                    blendMode = BlendMode.SrcIn,
                )
            },
        tint = Color.White,
    )
}

@Composable
private fun DownloadIcon(
    tint: Color,
    modifier: Modifier = Modifier,
) {
    Icon(
        imageVector = Icons.Rounded.Download,
        contentDescription = null,
        modifier = modifier,
        tint = tint,
    )
}
