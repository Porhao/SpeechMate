// Camera lighting & contrast check for live sessions.
//
// Samples the camera image once a second (tiny offscreen canvas) and measures:
//   - face brightness (inside the MediaPipe face box) and overall exposure
//   - backlight: background brighter than the face
//   - contrast: spread of brightness across the face (flat vs. defined)
//   - side balance: left vs. right half of the face (one-sided light)
//   - clipped highlights: share of blown-out face pixels
//   - separation: face vs. background luminance contrast ratio (WCAG formula)
// and turns them into specific, practical recommendations.

export interface FaceBox { x: number; y: number; w: number; h: number } // normalised 0–1, video frame coords

export interface LightingReport {
  status: "good" | "fair" | "poor";
  faceDetected: boolean;
  faceLum: number;        // 0–255
  frameLum: number;
  backgroundLum: number;
  contrast: number;       // std dev of face luminance
  sideDiff: number;       // |left − right| face luminance
  clippedPct: number;     // % of face pixels ≥ 245
  separation: number;     // face vs background contrast ratio (1–21)
  tips: string[];
}

const W = 96, H = 54;
let canvas: HTMLCanvasElement | null = null;

const lum = (r: number, g: number, b: number) => 0.2126 * r + 0.7152 * g + 0.0722 * b;
// WCAG relative luminance → contrast ratio between two grey levels
const rel = (v: number) => { const c = v / 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const ratio = (a: number, b: number) => { const [hi, lo] = [Math.max(rel(a), rel(b)), Math.min(rel(a), rel(b))]; return (hi + 0.05) / (lo + 0.05); };

export function analyzeLighting(video: HTMLVideoElement, face: FaceBox | null): LightingReport | null {
  if (video.readyState < 2 || !video.videoWidth) return null;
  canvas ??= document.createElement("canvas");
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.drawImage(video, 0, 0, W, H);
  const px = ctx.getImageData(0, 0, W, H).data;

  const box = face && {
    x0: Math.max(0, Math.floor(face.x * W)), x1: Math.min(W, Math.ceil((face.x + face.w) * W)),
    y0: Math.max(0, Math.floor(face.y * H)), y1: Math.min(H, Math.ceil((face.y + face.h) * H)),
  };
  let all = 0, n = 0, fSum = 0, fSq = 0, fN = 0, bSum = 0, bN = 0, left = 0, lN = 0, right = 0, rN = 0, clipped = 0;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      const l = lum(px[i], px[i + 1], px[i + 2]);
      all += l; n++;
      if (box && x >= box.x0 && x < box.x1 && y >= box.y0 && y < box.y1) {
        fSum += l; fSq += l * l; fN++;
        if (l >= 245) clipped++;
        // The image is not mirrored here, so "left" is the person's right side
        if (x < (box.x0 + box.x1) / 2) { left += l; lN++; } else { right += l; rN++; }
      } else { bSum += l; bN++; }
    }
  }
  const frameLum = all / n;
  const faceDetected = !!box && fN > 4;
  const faceLum = faceDetected ? fSum / fN : frameLum;
  const backgroundLum = faceDetected && bN ? bSum / bN : frameLum;
  const contrast = faceDetected ? Math.sqrt(Math.max(0, fSq / fN - (fSum / fN) ** 2)) : 0;
  const sideDiff = faceDetected && lN && rN ? Math.abs(left / lN - right / rN) : 0;
  const clippedPct = faceDetected ? (clipped / fN) * 100 : 0;
  const separation = ratio(faceLum, backgroundLum);

  const tips: string[] = [];
  let problems = 0;
  if (!faceDetected) tips.push("Centre your face in the frame so lighting can be checked on it.");
  if (faceLum < 70) { problems += 2; tips.push("Your face is very dark: put a lamp or a window in front of you, just above eye level."); }
  else if (faceLum < 90) { problems++; tips.push("Your face is a little dark: add a soft light in front of you (a desk lamp bounced off a wall works)."); }
  if (faceLum > 205 || clippedPct > 12) { problems++; tips.push("Your face is washed out: move the light further away or diffuse it (a sheet of paper or a curtain)."); }
  if (faceDetected && backgroundLum > faceLum + 15) { problems += 2; tips.push("Bright light behind you (backlit): turn to face the window or close the blinds behind you."); }
  if (faceDetected && contrast < 18) { problems++; tips.push("Very flat lighting: add a second light at about 45° to one side to give your face shape."); }
  if (sideDiff > 40) { problems++; tips.push("One side of your face is much darker: add light on that side or turn slightly towards your main light."); }
  if (faceDetected && separation < 1.3 && contrast >= 18) { problems++; tips.push("Your face blends into the background: a plainer background that is darker or lighter than your face will make you stand out."); }

  // Without a face we can't judge the lighting that matters, so never call it "good"
  const status = problems === 0 && faceDetected ? "good" : problems <= 2 ? "fair" : "poor";
  if (status === "good" && faceDetected) tips.push("Lighting looks good: your face is evenly lit and stands out from the background.");
  return { status, faceDetected, faceLum, frameLum, backgroundLum, contrast, sideDiff, clippedPct, separation, tips };
}
