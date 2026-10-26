import 'package:flutter/material.dart';
import 'dart:convert';
import 'dart:math' as math;

/// RealisticHandPainter renders an authentic, fleshy, 3D-shaded human hand
/// dynamically posed according to the 21 MediaPipe / ISL landmark coordinates.
class RealisticHandPainter extends CustomPainter {
  final List<dynamic> keypoints;
  final bool isGuideOverlay;
  final Color? guideColor;
  final bool showSkeleton;
  final bool showNails;
  final bool showCreases;

  RealisticHandPainter({
    required this.keypoints,
    this.isGuideOverlay = false,
    this.guideColor,
    this.showSkeleton = false,
    this.showNails = true,
    this.showCreases = true,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (keypoints.length < 21) return;

    // 1. Parse raw coordinates
    final List<Offset> rawPoints = [];
    double minX = 1.0, maxX = 0.0, minY = 1.0, maxY = 0.0;

    for (var kp in keypoints) {
      double x = 0.5;
      double y = 0.5;
      if (kp is Map) {
        x = (kp['x'] ?? 0.5).toDouble();
        y = (kp['y'] ?? 0.5).toDouble();
      } else if (kp is List && kp.length >= 2) {
        x = (kp[0] ?? 0.5).toDouble();
        y = (kp[1] ?? 0.5).toDouble();
      }
      minX = math.min(minX, x);
      maxX = math.max(maxX, x);
      minY = math.min(minY, y);
      maxY = math.max(maxY, y);
      rawPoints.add(Offset(x, y));
    }

    // Give bottom wrist margin so forearm base has room to anchor
    final contentW = math.max(0.01, maxX - minX);
    final contentH = math.max(0.01, (maxY - minY) * 1.15);
    const padding = 0.12;

    final scale = math.min(
      (size.width * (1.0 - 2 * padding)) / contentW,
      (size.height * (1.0 - 2 * padding)) / contentH,
    );

    final offsetX = (size.width - contentW * scale) / 2 - minX * scale;
    final offsetY = (size.height - contentH * scale) / 2 - minY * scale;

    final List<Offset> pts = [];
    for (var p in rawPoints) {
      pts.add(Offset(p.dx * scale + offsetX, p.dy * scale + offsetY));
    }

    if (pts.length < 21) return;

    // Base anatomical thickness scaled to canvas size
    final baseThickness = math.max(6.0, size.width * 0.076);

    // -------------------------------------------------------------
    // Helper Vector Functions
    // -------------------------------------------------------------
    Offset normalize(Offset v) {
      final len = v.distance;
      if (len < 0.0001) return const Offset(0, -1);
      return Offset(v.dx / len, v.dy / len);
    }

    Offset normalLeft(Offset dir) => Offset(-dir.dy, dir.dx);
    Offset normalRight(Offset dir) => Offset(dir.dy, -dir.dx);

    // -------------------------------------------------------------
    // Curled Detection (Finger folds over palm)
    // -------------------------------------------------------------
    bool isFingerCurled(int mcp, int pip, int dip, int tip) {
      final directDist = (pts[tip] - pts[mcp]).distance;
      final fullLength = (pts[pip] - pts[mcp]).distance +
          (pts[dip] - pts[pip]).distance +
          (pts[tip] - pts[dip]).distance;
      return directDist < (fullLength * 0.65);
    }

    final indexCurled = isFingerCurled(5, 6, 7, 8);
    final middleCurled = isFingerCurled(9, 10, 11, 12);
    final ringCurled = isFingerCurled(13, 14, 15, 16);
    final pinkyCurled = isFingerCurled(17, 18, 19, 20);
    final thumbCurled = (pts[4] - pts[2]).distance < ((pts[3] - pts[2]).distance + (pts[4] - pts[3]).distance) * 0.72;

    // -------------------------------------------------------------
    // Color Palette
    // -------------------------------------------------------------
    final effectiveGuideColor = guideColor ?? Colors.cyanAccent;

    // Skin tones
    const skinHighlight = Color(0xFFF7D6BD);
    const skinMid = Color(0xFFE8AD87);
    const skinShadow = Color(0xFFD48F66);
    const skinDeepCrease = Color(0xFFB3673F);
    const skinAmbientShadow = Color(0xFF6E3618);
    const nailBed = Color(0xFFFFF2EB);
    const nailCuticle = Color(0xFFDE9F79);

    final skinShader = LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: isGuideOverlay
          ? [
              effectiveGuideColor.withOpacity(0.28),
              effectiveGuideColor.withOpacity(0.18),
              effectiveGuideColor.withOpacity(0.12),
            ]
          : [skinHighlight, skinMid, skinShadow],
      stops: const [0.0, 0.55, 1.0],
    ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));

    final skinFillPaint = Paint()
      ..shader = skinShader
      ..style = PaintingStyle.fill;

    final skinStrokePaint = Paint()
      ..color = isGuideOverlay ? effectiveGuideColor.withOpacity(0.9) : const Color(0xFFC77E55)
      ..strokeWidth = isGuideOverlay ? 2.5 : 1.3
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..style = PaintingStyle.stroke;

    final ambientShadowPaint = Paint()
      ..color = skinAmbientShadow.withOpacity(0.15)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 5);

    // -------------------------------------------------------------
    // Finger Path Builder
    // -------------------------------------------------------------
    Path buildFingerPath(List<int> idxs, List<double> widthMultipliers) {
      final path = Path();
      final List<Offset> fingerJoints = [pts[idxs[0]], pts[idxs[1]], pts[idxs[2]], pts[idxs[3]]];
      final List<double> widths = widthMultipliers.map((m) => baseThickness * m).toList();

      final List<Offset> segDirs = [];
      final List<Offset> segNorms = [];
      for (int i = 0; i < 3; i++) {
        final d = normalize(fingerJoints[i + 1] - fingerJoints[i]);
        segDirs.add(d);
        segNorms.add(normalLeft(d));
      }

      // Joint normals (averaged)
      final List<Offset> jNorms = [];
      jNorms.add(segNorms[0]);
      jNorms.add(normalize(segNorms[0] + segNorms[1]));
      jNorms.add(normalize(segNorms[1] + segNorms[2]));
      jNorms.add(segNorms[2]);

      // Left side vertices
      final List<Offset> leftVerts = [];
      for (int i = 0; i < 4; i++) {
        leftVerts.add(fingerJoints[i] + jNorms[i] * (widths[i] / 2));
      }

      // Right side vertices
      final List<Offset> rightVerts = [];
      for (int i = 0; i < 4; i++) {
        rightVerts.add(fingerJoints[i] - jNorms[i] * (widths[i] / 2));
      }

      // Fingertip dome apex
      final tipApex = fingerJoints[3] + segDirs[2] * (widths[3] * 0.55);

      // Construct continuous smooth outline
      path.moveTo(leftVerts[0].dx, leftVerts[0].dy);
      path.lineTo(leftVerts[1].dx, leftVerts[1].dy);
      path.lineTo(leftVerts[2].dx, leftVerts[2].dy);
      path.lineTo(leftVerts[3].dx, leftVerts[3].dy);

      // Smooth rounded fingertip cap
      path.quadraticBezierTo(
        leftVerts[3].dx + segDirs[2].dx * (widths[3] * 0.4),
        leftVerts[3].dy + segDirs[2].dy * (widths[3] * 0.4),
        tipApex.dx,
        tipApex.dy,
      );
      path.quadraticBezierTo(
        rightVerts[3].dx + segDirs[2].dx * (widths[3] * 0.4),
        rightVerts[3].dy + segDirs[2].dy * (widths[3] * 0.4),
        rightVerts[3].dx,
        rightVerts[3].dy,
      );

      path.lineTo(rightVerts[2].dx, rightVerts[2].dy);
      path.lineTo(rightVerts[1].dx, rightVerts[1].dy);
      path.lineTo(rightVerts[0].dx, rightVerts[0].dy);
      path.close();

      return path;
    }

    // -------------------------------------------------------------
    // Palm & Wrist Forearm Path Builder
    // -------------------------------------------------------------
    Path buildPalmPath() {
      final path = Path();
      final p0 = pts[0];  // Wrist center
      final p9 = pts[9];  // Middle MCP

      // Wrist direction & normal
      final armDir = normalize(p0 - p9);
      final armNorm = normalLeft(armDir);
      final wristW = baseThickness * 2.5;

      final wLeft = p0 + armNorm * (wristW / 2);
      final wRight = p0 - armNorm * (wristW / 2);

      // Extended forearm cuff
      final fLeft = wLeft + armDir * (baseThickness * 1.3);
      final fRight = wRight + armDir * (baseThickness * 1.3);
      final fMid = p0 + armDir * (baseThickness * 1.5);

      // Outer Pinky side (Hypothenar eminence bulge)
      final p17 = pts[17];
      final hypoBulge = Offset(
        (wRight.dx + p17.dx) / 2 - armNorm.dx * (baseThickness * 0.35),
        (wRight.dy + p17.dy) / 2 - armNorm.dy * (baseThickness * 0.35),
      );

      // Knuckles
      final p13 = pts[13];
      final p5 = pts[5];

      // Webbing dips between fingers
      final webPinkyRing = Offset((p17.dx + p13.dx) / 2, (p17.dy + p13.dy) / 2);
      final webRingMid = Offset((p13.dx + p9.dx) / 2, (p13.dy + p9.dy) / 2);
      final webMidIdx = Offset((p9.dx + p5.dx) / 2, (p9.dy + p5.dy) / 2);

      // Deep valley between index and thumb
      final p2 = pts[2];
      final p1 = pts[1];
      final thumbWebbing = Offset(p5.dx * 0.35 + p2.dx * 0.65, p5.dy * 0.35 + p2.dy * 0.65);

      // Thenar eminence (fleshy thumb muscle pad)
      final thenarBulge = Offset(
        p1.dx + armNorm.dx * (baseThickness * 0.6),
        p1.dy + armNorm.dy * (baseThickness * 0.6),
      );

      path.moveTo(wLeft.dx, wLeft.dy);
      // Forearm bottom anchor
      path.lineTo(fLeft.dx, fLeft.dy);
      path.quadraticBezierTo(fMid.dx, fMid.dy, fRight.dx, fRight.dy);
      path.lineTo(wRight.dx, wRight.dy);

      // Pinky edge
      path.quadraticBezierTo(hypoBulge.dx, hypoBulge.dy, p17.dx, p17.dy);

      // Knuckle arches with webbing
      path.quadraticBezierTo(p17.dx, p17.dy, webPinkyRing.dx, webPinkyRing.dy);
      path.quadraticBezierTo(p13.dx, p13.dy, webRingMid.dx, webRingMid.dy);
      path.quadraticBezierTo(p9.dx, p9.dy, webMidIdx.dx, webMidIdx.dy);
      path.quadraticBezierTo(p5.dx, p5.dy, thumbWebbing.dx, thumbWebbing.dy);

      // Thumb base & thenar eminence
      path.quadraticBezierTo(p2.dx, p2.dy, thenarBulge.dx, thenarBulge.dy);
      path.quadraticBezierTo(thenarBulge.dx, thenarBulge.dy, wLeft.dx, wLeft.dy);
      path.close();

      return path;
    }

    // -------------------------------------------------------------
    // Construct Path Elements
    // -------------------------------------------------------------
    final thumbPath = buildFingerPath([1, 2, 3, 4], [1.35, 1.25, 1.12, 0.95]);
    final indexPath = buildFingerPath([5, 6, 7, 8], [1.15, 1.05, 0.95, 0.82]);
    final middlePath = buildFingerPath([9, 10, 11, 12], [1.20, 1.10, 1.00, 0.85]);
    final ringPath = buildFingerPath([13, 14, 15, 16], [1.10, 1.00, 0.90, 0.78]);
    final pinkyPath = buildFingerPath([17, 18, 19, 20], [0.95, 0.85, 0.75, 0.65]);
    final palmPath = buildPalmPath();

    // -------------------------------------------------------------
    // 2. Ambient Drop Shadow (Real 3D Depth)
    // -------------------------------------------------------------
    if (!isGuideOverlay) {
      canvas.save();
      canvas.translate(2.5, 4.0);
      canvas.drawPath(palmPath, ambientShadowPaint);
      if (!indexCurled) canvas.drawPath(indexPath, ambientShadowPaint);
      if (!middleCurled) canvas.drawPath(middlePath, ambientShadowPaint);
      if (!ringCurled) canvas.drawPath(ringPath, ambientShadowPaint);
      if (!pinkyCurled) canvas.drawPath(pinkyPath, ambientShadowPaint);
      if (!thumbCurled) canvas.drawPath(thumbPath, ambientShadowPaint);
      canvas.restore();
    }

    // -------------------------------------------------------------
    // 3. Render Extended Fingers (Background Layer)
    // -------------------------------------------------------------
    void drawFinger(Path fPath) {
      canvas.drawPath(fPath, skinFillPaint);
      canvas.drawPath(fPath, skinStrokePaint);
    }

    if (!pinkyCurled) drawFinger(pinkyPath);
    if (!ringCurled) drawFinger(ringPath);
    if (!middleCurled) drawFinger(middlePath);
    if (!indexCurled) drawFinger(indexPath);
    if (!thumbCurled) drawFinger(thumbPath);

    // -------------------------------------------------------------
    // 4. Render Palm Body & Forearm
    // -------------------------------------------------------------
    canvas.drawPath(palmPath, skinFillPaint);
    canvas.drawPath(palmPath, skinStrokePaint);

    // -------------------------------------------------------------
    // 5. Render Curled Fingers Over Palm (With Soft Drop Shadow)
    // -------------------------------------------------------------
    void drawCurledFinger(Path fPath) {
      if (!isGuideOverlay) {
        canvas.save();
        canvas.translate(1.5, 2.5);
        canvas.drawPath(fPath, ambientShadowPaint);
        canvas.restore();
      }
      canvas.drawPath(fPath, skinFillPaint);
      canvas.drawPath(fPath, skinStrokePaint);
    }

    if (pinkyCurled) drawCurledFinger(pinkyPath);
    if (ringCurled) drawCurledFinger(ringPath);
    if (middleCurled) drawCurledFinger(middlePath);
    if (indexCurled) drawCurledFinger(indexPath);
    if (thumbCurled) drawCurledFinger(thumbPath);

    // -------------------------------------------------------------
    // 6. Natural Anatomical Palm Creases (Life & Heart Lines)
    // -------------------------------------------------------------
    if (!isGuideOverlay && showCreases) {
      final creasePaint = Paint()
        ..color = skinDeepCrease.withOpacity(0.38)
        ..strokeWidth = math.max(1.2, baseThickness * 0.12)
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;

      // Heart line (Upper palm curve below knuckles)
      final heartLine = Path()
        ..moveTo(pts[17].dx - baseThickness * 0.2, pts[17].dy + baseThickness * 0.5)
        ..quadraticBezierTo(
          pts[9].dx,
          pts[9].dy + baseThickness * 0.8,
          pts[5].dx + baseThickness * 0.2,
          pts[5].dy + baseThickness * 0.9,
        );
      canvas.drawPath(heartLine, creasePaint);

      // Head / Life line (Curving around thenar eminence)
      final lifeLine = Path()
        ..moveTo(pts[5].dx * 0.7 + pts[2].dx * 0.3, pts[5].dy * 0.7 + pts[2].dy * 0.3)
        ..quadraticBezierTo(
          pts[0].dx + baseThickness * 0.4,
          (pts[9].dy + pts[0].dy) / 2,
          pts[0].dx,
          pts[0].dy - baseThickness * 0.4,
        );
      canvas.drawPath(lifeLine, creasePaint);

      // Knuckle subtle skin fold marks
      for (var kIdx in [5, 9, 13, 17]) {
        final kp = pts[kIdx];
        final fold = Path()
          ..moveTo(kp.dx - baseThickness * 0.35, kp.dy)
          ..quadraticBezierTo(kp.dx, kp.dy + baseThickness * 0.15, kp.dx + baseThickness * 0.35, kp.dy);
        canvas.drawPath(fold, creasePaint..color = skinDeepCrease.withOpacity(0.25));
      }
    }

    // -------------------------------------------------------------
    // 7. Finger Joint Creases & Nails
    // -------------------------------------------------------------
    void drawCreaseArc(Offset p, Offset dir, double w) {
      if (isGuideOverlay || !showCreases) return;
      final n = normalLeft(dir);
      final cPaint = Paint()
        ..color = skinDeepCrease.withOpacity(0.32)
        ..strokeWidth = math.max(1.0, baseThickness * 0.1)
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;

      final p1 = p - n * (w * 0.38);
      final p2 = p + n * (w * 0.38);
      final ctrl = p + dir * (w * 0.1);
      final path = Path()
        ..moveTo(p1.dx, p1.dy)
        ..quadraticBezierTo(ctrl.dx, ctrl.dy, p2.dx, p2.dy);
      canvas.drawPath(path, cPaint);
    }

    void drawFingernail(Offset tip, Offset prev, double w) {
      if (isGuideOverlay || !showNails) return;
      final dir = normalize(tip - prev);
      final n = normalLeft(dir);
      final nailW = w * 0.62;
      final nailH = w * 0.75;
      final nailCenter = tip - dir * (nailH * 0.45);

      canvas.save();
      canvas.translate(nailCenter.dx, nailCenter.dy);
      final angle = math.atan2(dir.dy, dir.dx) - math.pi / 2;
      canvas.rotate(angle);

      final rrect = RRect.fromRectAndRadius(
        Rect.fromCenter(center: Offset.zero, width: nailW, height: nailH),
        Radius.circular(nailW * 0.42),
      );

      final nailFill = Paint()
        ..color = nailBed.withOpacity(0.85)
        ..style = PaintingStyle.fill;
      final nailStroke = Paint()
        ..color = nailCuticle.withOpacity(0.55)
        ..strokeWidth = 0.8
        ..style = PaintingStyle.stroke;

      canvas.drawRRect(rrect, nailFill);
      canvas.drawRRect(rrect, nailStroke);

      // Subtle lunula crescent
      final lunula = Path()
        ..moveTo(-nailW * 0.3, nailH * 0.3)
        ..quadraticBezierTo(0, nailH * 0.12, nailW * 0.3, nailH * 0.3);
      canvas.drawPath(
        lunula,
        Paint()
          ..color = Colors.white.withOpacity(0.4)
          ..strokeWidth = 0.9
          ..style = PaintingStyle.stroke,
      );

      canvas.restore();
    }

    // Draw creases and nails for extended fingers
    if (!thumbCurled) {
      drawCreaseArc(pts[2], normalize(pts[3] - pts[2]), baseThickness * 1.25);
      drawCreaseArc(pts[3], normalize(pts[4] - pts[3]), baseThickness * 1.12);
      drawFingernail(pts[4], pts[3], baseThickness * 0.95);
    }
    if (!indexCurled) {
      drawCreaseArc(pts[6], normalize(pts[7] - pts[6]), baseThickness * 1.05);
      drawCreaseArc(pts[7], normalize(pts[8] - pts[7]), baseThickness * 0.95);
      drawFingernail(pts[8], pts[7], baseThickness * 0.82);
    }
    if (!middleCurled) {
      drawCreaseArc(pts[10], normalize(pts[11] - pts[10]), baseThickness * 1.10);
      drawCreaseArc(pts[11], normalize(pts[12] - pts[11]), baseThickness * 1.00);
      drawFingernail(pts[12], pts[11], baseThickness * 0.85);
    }
    if (!ringCurled) {
      drawCreaseArc(pts[14], normalize(pts[15] - pts[14]), baseThickness * 1.00);
      drawCreaseArc(pts[15], normalize(pts[16] - pts[15]), baseThickness * 0.90);
      drawFingernail(pts[16], pts[15], baseThickness * 0.78);
    }
    if (!pinkyCurled) {
      drawCreaseArc(pts[18], normalize(pts[19] - pts[18]), baseThickness * 0.85);
      drawCreaseArc(pts[19], normalize(pts[20] - pts[19]), baseThickness * 0.75);
      drawFingernail(pts[20], pts[19], baseThickness * 0.65);
    }

    // -------------------------------------------------------------
    // 8. Optional Skeleton Overlay (X-Ray Mode)
    // -------------------------------------------------------------
    if (showSkeleton) {
      final bonePaint = Paint()
        ..color = Colors.deepPurple.withOpacity(0.85)
        ..strokeWidth = 2.0
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;

      void drawBone(int a, int b) {
        if (a < pts.length && b < pts.length) {
          canvas.drawLine(pts[a], pts[b], bonePaint);
        }
      }

      drawBone(0, 1); drawBone(1, 2); drawBone(2, 3); drawBone(3, 4);
      drawBone(0, 5); drawBone(5, 6); drawBone(6, 7); drawBone(7, 8);
      drawBone(0, 9); drawBone(9, 10); drawBone(10, 11); drawBone(11, 12);
      drawBone(0, 13); drawBone(13, 14); drawBone(14, 15); drawBone(15, 16);
      drawBone(0, 17); drawBone(17, 18); drawBone(18, 19); drawBone(19, 20);

      final nodePaint = Paint()..color = Colors.white..style = PaintingStyle.fill;
      final ringPaint = Paint()..color = Colors.deepPurple..strokeWidth = 1.5..style = PaintingStyle.stroke;

      for (var p in pts) {
        canvas.drawCircle(p, 3.5, nodePaint);
        canvas.drawCircle(p, 3.5, ringPaint);
      }
    }

    // -------------------------------------------------------------
    // 9. Guide Overlay Targets (when used on Camera View)
    // -------------------------------------------------------------
    if (isGuideOverlay) {
      final tips = [4, 8, 12, 16, 20];
      final targetGlow = Paint()
        ..color = effectiveGuideColor.withOpacity(0.4)
        ..style = PaintingStyle.fill;
      final targetCore = Paint()
        ..color = Colors.white
        ..style = PaintingStyle.fill;

      for (var tIdx in tips) {
        final tp = pts[tIdx];
        canvas.drawCircle(tp, 9.0, targetGlow);
        canvas.drawCircle(tp, 4.0, Paint()..color = effectiveGuideColor);
        canvas.drawCircle(tp, 2.0, targetCore);
      }
    }
  }

  @override
  bool shouldRepaint(covariant RealisticHandPainter oldDelegate) {
    return oldDelegate.keypoints != keypoints ||
        oldDelegate.isGuideOverlay != isGuideOverlay ||
        oldDelegate.guideColor != guideColor ||
        oldDelegate.showSkeleton != showSkeleton ||
        oldDelegate.showNails != showNails ||
        oldDelegate.showCreases != showCreases;
  }
}

/// HandSkeletonPainter legacy compatibility class that delegates to RealisticHandPainter
class HandSkeletonPainter extends CustomPainter {
  final List<dynamic> keypoints;
  final bool isGuideOverlay;
  final Color? customColor;
  final double boneWidth;
  final double jointRadius;
  final bool showSkeleton;

  HandSkeletonPainter({
    required this.keypoints,
    this.isGuideOverlay = false,
    this.customColor,
    this.boneWidth = 3.0,
    this.jointRadius = 4.5,
    this.showSkeleton = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final painter = RealisticHandPainter(
      keypoints: keypoints,
      isGuideOverlay: isGuideOverlay,
      guideColor: customColor,
      showSkeleton: showSkeleton,
    );
    painter.paint(canvas, size);
  }

  @override
  bool shouldRepaint(covariant HandSkeletonPainter oldDelegate) {
    return oldDelegate.keypoints != keypoints ||
        oldDelegate.isGuideOverlay != isGuideOverlay ||
        oldDelegate.customColor != customColor ||
        oldDelegate.showSkeleton != showSkeleton;
  }
}

/// LiveHandTrackingPainter paints the user's REAL live tracked hand on camera
class LiveHandTrackingPainter extends CustomPainter {
  final List<dynamic>? keypoints;
  final bool isMatched;
  final bool mirrorFrontCamera;

  LiveHandTrackingPainter({
    required this.keypoints,
    this.isMatched = false,
    this.mirrorFrontCamera = true,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (keypoints == null || keypoints!.length < 21) return;

    final List<Offset> points = [];
    for (var kp in keypoints!) {
      double normX = 0.5;
      double normY = 0.5;
      if (kp is Map) {
        normX = (kp['x'] ?? 0.5).toDouble();
        normY = (kp['y'] ?? 0.5).toDouble();
      } else if (kp is List && kp.length >= 2) {
        normX = (kp[0] ?? 0.5).toDouble();
        normY = (kp[1] ?? 0.5).toDouble();
      }

      final screenX = (mirrorFrontCamera ? (1.0 - normX) : normX) * size.width;
      final screenY = normY * size.height;
      points.add(Offset(screenX, screenY));
    }

    final primaryColor = isMatched ? const Color(0xFF00E676) : const Color(0xFF00E5FF);
    final glowColor = isMatched ? Colors.greenAccent : Colors.cyanAccent;

    final bonePaint = Paint()
      ..color = primaryColor.withOpacity(0.9)
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final glowPaint = Paint()
      ..color = glowColor.withOpacity(0.3)
      ..strokeWidth = 7.0
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    void drawLiveBone(int start, int end) {
      if (start < points.length && end < points.length) {
        canvas.drawLine(points[start], points[end], glowPaint);
        canvas.drawLine(points[start], points[end], bonePaint);
      }
    }

    // Palm bones
    drawLiveBone(0, 1);
    drawLiveBone(0, 5);
    drawLiveBone(0, 17);
    drawLiveBone(5, 9);
    drawLiveBone(9, 13);
    drawLiveBone(13, 17);

    // Five fingers
    drawLiveBone(1, 2); drawLiveBone(2, 3); drawLiveBone(3, 4);
    drawLiveBone(5, 6); drawLiveBone(6, 7); drawLiveBone(7, 8);
    drawLiveBone(9, 10); drawLiveBone(10, 11); drawLiveBone(11, 12);
    drawLiveBone(13, 14); drawLiveBone(14, 15); drawLiveBone(15, 16);
    drawLiveBone(17, 18); drawLiveBone(18, 19); drawLiveBone(19, 20);

    // Joint dots
    final jointDot = Paint()..color = Colors.white..style = PaintingStyle.fill;
    final jointRing = Paint()..color = primaryColor..strokeWidth = 1.5..style = PaintingStyle.stroke;

    for (int i = 0; i < points.length; i++) {
      final p = points[i];
      canvas.drawCircle(p, 4.0, jointDot);
      canvas.drawCircle(p, 4.0, jointRing);
    }

    // Fingertip glowing indicators
    final tips = [4, 8, 12, 16, 20];
    final tipGlow = Paint()..color = glowColor.withOpacity(0.5)..style = PaintingStyle.fill;
    final tipCore = Paint()..color = primaryColor..style = PaintingStyle.fill;

    for (var tipIdx in tips) {
      if (tipIdx < points.length) {
        final p = points[tipIdx];
        canvas.drawCircle(p, 10.0, tipGlow);
        canvas.drawCircle(p, 6.0, tipCore);
        canvas.drawCircle(p, 2.5, jointDot);
      }
    }
  }

  @override
  bool shouldRepaint(covariant LiveHandTrackingPainter oldDelegate) {
    return oldDelegate.keypoints != keypoints || oldDelegate.isMatched != isMatched;
  }
}

/// HandSkeletonWidget renders a PROPER REALISTIC HUMAN HAND (Proper Haat ✋)
/// with natural skin tones, fleshy fingers, palm creases, and fingernails.
class HandSkeletonWidget extends StatelessWidget {
  final dynamic keypoints;
  final double width;
  final double height;
  final Color? backgroundColor;
  final bool isGuideOverlay;
  final Color? guideColor;
  final bool showSkeleton;

  const HandSkeletonWidget({
    Key? key,
    required this.keypoints,
    this.width = 120,
    this.height = 120,
    this.backgroundColor,
    this.isGuideOverlay = false,
    this.guideColor,
    this.showSkeleton = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    List<dynamic> parsedPoints = [];

    if (keypoints is String && (keypoints as String).isNotEmpty) {
      try {
        parsedPoints = jsonDecode(keypoints as String);
      } catch (e) {
        parsedPoints = [];
      }
    } else if (keypoints is List) {
      parsedPoints = keypoints as List;
    }

    if (parsedPoints.length < 21) {
      return Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: backgroundColor ?? (isGuideOverlay ? Colors.transparent : Colors.grey.shade100),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Center(
          child: Icon(
            Icons.pan_tool_rounded,
            color: isGuideOverlay ? Colors.white54 : Colors.grey.shade400,
            size: width * 0.35,
          ),
        ),
      );
    }

    return Container(
      width: width,
      height: height,
      padding: EdgeInsets.all(isGuideOverlay ? 4 : 6),
      decoration: BoxDecoration(
        color: backgroundColor ?? (isGuideOverlay
            ? Colors.black.withOpacity(0.25)
            : const Color(0xFFFAF5F0)), // Soft warm neutral card canvas
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isGuideOverlay
              ? (guideColor ?? Colors.cyanAccent).withOpacity(0.4)
              : Colors.deepPurple.shade100.withOpacity(0.6),
          width: isGuideOverlay ? 1.5 : 1.0,
        ),
      ),
      child: CustomPaint(
        painter: RealisticHandPainter(
          keypoints: parsedPoints,
          isGuideOverlay: isGuideOverlay,
          guideColor: guideColor,
          showSkeleton: showSkeleton,
        ),
      ),
    );
  }
}
