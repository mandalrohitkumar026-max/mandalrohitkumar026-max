import os
import math
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter, map_coordinates

def generate_banner_animation():
    src_path = "banner.jpg"
    if not os.path.exists(src_path):
        print(f"Error: {src_path} not found")
        return

    base_img = Image.open(src_path).convert("RGB")
    W, H = base_img.size
    print(f"Loaded {src_path} ({W}x{H})")

    # Save static fallback PNG
    base_img.save("banner.png", "PNG", optimize=True)
    print("Saved static fallback banner.png")

    arr = np.array(base_img, dtype=np.float32)

    # Color masks
    # Cyan: high G & B, lower R
    cyan_mask = (arr[:, :, 1] > 80) & (arr[:, :, 2] > 80) & (arr[:, :, 0] < 120)
    # Purple/Magenta: high R & B, lower G
    purple_mask = (arr[:, :, 0] > 80) & (arr[:, :, 2] > 80) & (arr[:, :, 1] < 100)
    
    # Soften masks
    cyan_float = gaussian_filter(cyan_mask.astype(np.float32), sigma=1.0)
    purple_float = gaussian_filter(purple_mask.astype(np.float32), sigma=1.0)

    # Coordinates grids
    y_indices, x_indices = np.indices((H, W), dtype=np.float32)

    # Monitors Bounding Boxes
    # Mon 1 (Code): x in [422, 538], y in [70, 192]
    m1_mask = (x_indices >= 422) & (x_indices <= 538) & (y_indices >= 70) & (y_indices <= 192)
    # Mon 2 (Chart): x in [550, 678], y in [46, 170]
    m2_mask = (x_indices >= 550) & (x_indices <= 678) & (y_indices >= 46) & (y_indices <= 170)
    # Mon 3 (Lower map): x in [482, 634], y in [198, 288]
    m3_mask = (x_indices >= 482) & (x_indices <= 634) & (y_indices >= 198) & (y_indices <= 288)

    # Torso breathing mask (y in [175, 335], x in [185, 435])
    torso_mask = np.zeros((H, W), dtype=np.float32)
    for y in range(175, min(335, H)):
        wy = math.sin(math.pi * (y - 175) / (335 - 175))
        for x in range(185, 435):
            wx = math.sin(math.pi * (x - 185) / (435 - 185))
            torso_mask[y, x] = wy * wx

    # Subtle floating particles (14 particles with fixed seed)
    rng = np.random.RandomState(42)
    particles = []
    for _ in range(14):
        px = rng.uniform(20, W - 20)
        py = rng.uniform(20, H - 20)
        speed = rng.uniform(25, 45) # pixels per loop
        color = rng.choice(["cyan", "purple"])
        particles.append((px, py, speed, color))

    # Pre-calculate soft monitor ambient glow
    monitor_glow = np.zeros((H, W), dtype=np.float32)
    center_mx, center_my = 550.0, 160.0
    dist_sq = ((x_indices - center_mx) ** 2) / (180.0 ** 2) + ((y_indices - center_my) ** 2) / (100.0 ** 2)
    monitor_glow = np.exp(-dist_sq).astype(np.float32)

    # 48 frames at 170ms = 8.16 seconds duration
    num_frames = 48
    frame_duration_ms = 170
    frames = []

    print(f"Generating {num_frames} frames for a seamless ~8.16s loop...")

    for i in range(num_frames):
        t = i / float(num_frames) # 0.0 to (N-1)/N
        theta = 2.0 * math.pi * t # 0 to 2pi (perfect loop)

        frame = arr.copy()

        # 1. Subtle Torso Breathing (0.6px vertical wave)
        dy_breath = 0.6 * math.sin(theta)
        if abs(dy_breath) > 0.01:
            # Warp torso coordinates
            cur_y = y_indices - dy_breath * torso_mask
            cur_x = x_indices
            coords = np.array([cur_y, cur_x])
            for c in range(3):
                frame[:, :, c] = map_coordinates(frame[:, :, c], coords, order=1, mode='nearest')

        # 2. Cyberpunk Lighting & Neon Pulses
        flicker = 1.0 - 0.04 * math.exp(-((t - 0.74) / 0.02) ** 2)
        
        cyan_factor = (1.0 + 0.12 * math.sin(theta)) * flicker
        purple_factor = (1.0 + 0.12 * math.sin(theta + 2.0 * math.pi / 3.0)) * flicker

        # Apply neon pulse to cyan channels (G, B)
        frame[:, :, 1] = np.clip(frame[:, :, 1] * (1.0 + (cyan_factor - 1.0) * cyan_float), 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * (1.0 + (cyan_factor - 1.0) * cyan_float), 0, 255)

        # Apply neon pulse to purple channels (R, B)
        frame[:, :, 0] = np.clip(frame[:, :, 0] * (1.0 + (purple_factor - 1.0) * purple_float), 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * (1.0 + (purple_factor - 1.0) * purple_float), 0, 255)

        # Ambient monitor screen glow breathing (soft cyan cast)
        glow_pulse = 0.08 * math.sin(theta)
        frame[:, :, 1] = np.clip(frame[:, :, 1] + 16.0 * monitor_glow * (1.0 + glow_pulse), 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] + 24.0 * monitor_glow * (1.0 + glow_pulse), 0, 255)

        # 3. Monitor Animations
        # Mon 1: Code editor slow scan sweep + Blinking cursor
        # Sweep line down code monitor
        sweep_y = 70 + int((t * 122.0) % 122.0)
        if 70 <= sweep_y < 192:
            sweep_mask = m1_mask & (np.abs(y_indices - sweep_y) <= 1.5)
            frame[sweep_mask, 1] = np.clip(frame[sweep_mask, 1] * 1.25, 0, 255)
            frame[sweep_mask, 2] = np.clip(frame[sweep_mask, 2] * 1.35, 0, 255)

        # Blinking cursor in code editor (blinks ~4 times per loop)
        cursor_visible = math.sin(theta * 4.0) > 0.0
        if cursor_visible:
            # Draw tiny cyan cursor rectangle at (x: 486..488, y: 172..175)
            frame[172:176, 486:489, 0] = 50
            frame[172:176, 486:489, 1] = 255
            frame[172:176, 486:489, 2] = 255

        # Mon 2: Chart line subtle data flow
        chart_wave = np.sin((x_indices - 550.0) * 0.15 - theta)
        chart_boost = (m2_mask & (arr[:, :, 1] > 60)) * (0.15 * chart_wave)
        frame[:, :, 1] = np.clip(frame[:, :, 1] * (1.0 + chart_boost), 0, 255)
        frame[:, :, 2] = np.clip(frame[:, :, 2] * (1.0 + chart_boost * 0.8), 0, 255)

        # Mon 3: Map radar ping node at (562, 238)
        ping_r = (t * 28.0) % 28.0
        ping_dist = np.sqrt((x_indices - 562.0) ** 2 + (y_indices - 238.0) ** 2)
        ping_ring = (m3_mask) & (np.abs(ping_dist - ping_r) <= 1.0)
        ping_intensity = (1.0 - ping_r / 28.0) * 0.6
        frame[ping_ring, 1] = np.clip(frame[ping_ring, 1] + 180 * ping_intensity, 0, 255)
        frame[ping_ring, 2] = np.clip(frame[ping_ring, 2] + 220 * ping_intensity, 0, 255)

        # 4. Subtle moving scanline (repeats exactly over the loop)
        scan_offset = theta
        scan_factor = 1.0 - 0.025 * (np.sin(y_indices * 1.5 - scan_offset) > 0.80)
        frame = frame * scan_factor[:, :, np.newaxis]

        # 5. Floating subtle cyber particles
        for (px, py, spd, col) in particles:
            cur_p_y = int((py - spd * t) % H)
            cur_p_x = int(px)
            # Only draw in darker regions to keep text pristine
            if 1 <= cur_p_y < H - 1 and 1 <= cur_p_x < W - 1:
                if np.mean(arr[cur_p_y, cur_p_x]) < 70:
                    alpha = math.sin(math.pi * cur_p_y / H) # Fades at top and bottom
                    if col == "cyan":
                        frame[cur_p_y, cur_p_x, 1] = min(255, frame[cur_p_y, cur_p_x, 1] + 120 * alpha)
                        frame[cur_p_y, cur_p_x, 2] = min(255, frame[cur_p_y, cur_p_x, 2] + 160 * alpha)
                    else:
                        frame[cur_p_y, cur_p_x, 0] = min(255, frame[cur_p_y, cur_p_x, 0] + 150 * alpha)
                        frame[cur_p_y, cur_p_x, 2] = min(255, frame[cur_p_y, cur_p_x, 2] + 160 * alpha)

        # 6. Camera Push-In / Zoom (1.0 -> 1.035 -> 1.0)
        zoom = 1.0 + 0.035 * ((1.0 - math.cos(theta)) / 2.0)
        
        # Convert to PIL Image
        pil_frame = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8), mode='RGB')

        if zoom > 1.0005:
            # Crop centered on Rohit & cockpit (center: cx ~ 0.42*W, cy ~ 0.52*H)
            cx, cy = 0.42 * W, 0.52 * H
            crop_w = W / zoom
            crop_h = H / zoom
            left = cx - crop_w / 2.0
            top = cy - crop_h / 2.0
            right = left + crop_w
            bottom = top + crop_h

            cropped = pil_frame.crop((left, top, right, bottom))
            pil_frame = cropped.resize((W, H), Image.Resampling.LANCZOS)

        frames.append(pil_frame)

    print("Frames generation complete. Quantizing and saving optimized GIF...")

    # Generate master palette from key frames to prevent color banding/stutter
    # Combine 4 key frames evenly spaced
    palette_sample = Image.new("RGB", (W * 2, H * 2))
    palette_sample.paste(frames[0], (0, 0))
    palette_sample.paste(frames[num_frames // 4], (W, 0))
    palette_sample.paste(frames[num_frames // 2], (0, H))
    palette_sample.paste(frames[3 * num_frames // 4], (W, H))

    master_palette_img = palette_sample.quantize(colors=256, method=Image.Resampling.LANCZOS)

    # Quantize each frame against master palette
    p_frames = []
    for f in frames:
        p_frame = f.quantize(palette=master_palette_img, dither=Image.Dither.FLOYDSTEINBERG)
        p_frames.append(p_frame)

    out_gif = "banner.gif"
    p_frames[0].save(
        out_gif,
        save_all=True,
        append_images=p_frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True
    )

    size_mb = os.path.getsize(out_gif) / (1024 * 1024)
    print(f"SUCCESS: Saved {out_gif} ({size_mb:.2f} MB), {num_frames} frames, {num_frames * frame_duration_ms / 1000.0:.2f}s loop.")

if __name__ == "__main__":
    generate_banner_animation()
