import io, os, zipfile, datetime
import streamlit as st
from PIL import Image, ImageOps
from pdf2image import convert_from_bytes
from pillow_heif import register_heif_opener

register_heif_opener()

st.set_page_config(page_title="画像変換アプリ", page_icon="✨", layout="centered")
st.title("✨ 画像変換アプリ（JPEG出力）")
st.write("PNG / JPEG / BMP / HEIC / PDF → 高画質なJPEGに変換します。")
st.write("・1枚のとき：JPEGをそのままダウンロード\n\n・2枚以上のとき：ZIPにまとめてダウンロード")

with st.sidebar:
    st.header("⚙️ 設定")
    target_w = st.slider("幅(px)", 400, 3000, 1200, 100)
    quality = st.slider("画質", 60, 100, 95, 1)
    keep = st.checkbox("元サイズを保持（リサイズしない）", value=False)
    dpi = st.slider("PDF DPI", 100, 400, 200, 50)

uploaded = st.file_uploader(
    "📁 ファイルを選択（複数可）",
    type=["png", "jpg", "jpeg", "bmp", "pdf", "heic", "heif"],
    accept_multiple_files=True,
)

def convert_image(img, target_w, quality, keep):
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if (not keep) and img.size[0] > target_w:
        ratio = target_w / float(img.size[0])
        new_h = int(img.size[1] * ratio)
        img = img.resize((target_w, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue(), img.size

if st.button("🚀 変換する", type="primary", use_container_width=True):
    if not uploaded:
        st.warning("⚠️ まずファイルを選択してください。")
    else:
        results = []
        total_in = 0
        progress = st.progress(0.0)
        log = st.empty()
        lines = []
        for idx, f in enumerate(uploaded, 1):
            content = f.read()
            base = os.path.splitext(f.name)[0]
            total_in += len(content)
            lines.append(f"📄 {f.name} ({len(content)/1024:.1f} KB)")
            try:
                if f.name.lower().endswith(".pdf"):
                    pages = convert_from_bytes(content, dpi=dpi)
                    for i, page in enumerate(pages, 1):
                        data, sz = convert_image(page, target_w, quality, keep)
                        out_name = f"{base}_p{i}.jpg"
                        results.append((out_name, data, sz))
                        lines.append(f"   → {out_name}  {sz[0]}x{sz[1]} ({len(data)/1024:.1f} KB)")
                else:
                    img = Image.open(io.BytesIO(content))
                    data, sz = convert_image(img, target_w, quality, keep)
                    out_name = f"{base}_converted.jpg"
                    results.append((out_name, data, sz))
                    lines.append(f"   → {out_name}  {sz[0]}x{sz[1]} ({len(data)/1024:.1f} KB)")
            except Exception as e:
                lines.append(f"   ❌ エラー: {e}")
            progress.progress(idx / len(uploaded))
            log.text("\n".join(lines))

        if not results:
            st.error("変換できたファイルがありませんでした。")
        else:
            total_out = sum(len(d) for _, d, _ in results)
            st.success(f"✅ 完了: {len(results)} ファイル  {total_in/1024/1024:.2f} MB → {total_out/1024/1024:.2f} MB")
            if len(results) == 1:
                out_name, data, _ = results[0]
                st.image(data, caption=out_name, use_container_width=True)
                st.download_button("⬇️ JPEGをダウンロード", data=data, file_name=out_name, mime="image/jpeg")
            else:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for out_name, data, _ in results:
                        zf.writestr(out_name, data)
                st.download_button(
                    "📦 ZIPをダウンロード",
                    data=zip_buf.getvalue(),
                    file_name=f"converted_{ts}.zip",
                    mime="application/zip",
                )
