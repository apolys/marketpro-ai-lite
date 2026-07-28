#!/usr/bin/env python3
# ============================================
# demo_app.py — 로컬 시연용 테스트 페이지
#
# YOLO -> OCR -> SKU 매칭 파이프라인을 브라우저에서
# 이미지 업로드 + 버튼 클릭만으로 바로 확인할 수 있게 만든 데모 서버.
#
# ⚠️ main.py(S3 기반 프로덕션 API)와는 완전히 별개의 파일입니다.
#    main.py의 인터페이스 계약을 건드리지 않기 위해 분리했습니다.
#
# 실행 방법 (프로젝트 루트, marketpro-ai-lite/ 에서):
#     python3 demo_app.py
#   또는
#     uvicorn demo_app:app --reload --port 8010
#
# 접속:
#     http://127.0.0.1:8010
# ============================================

import base64
import io

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image, ImageDraw, ImageOps

from app.yolo_engine import detect_products
from app.ocr_engine import extract_price
from app.sku_engine import match_sku, match_catalog_text

app = FastAPI(title="MarketPro AI Lite - 로컬 데모")

# 시연용 박스 색상
PRICE_COLOR = (0, 170, 0)      # 가격표로 인식된 텍스트 - 초록
NAME_COLOR = (0, 110, 230)     # 상품명 후보 텍스트 - 파랑
BANNER_COLOR = (210, 0, 0)     # 대형 배너로 걸러진 텍스트 - 빨강


def _draw_annotations(pil_img, ocr_blocks):
    """OCR이 실제로 어떤 영역을 어떻게 분류했는지 이미지 위에 색깔 박스로 표시 (시연/디버깅용)"""
    img = pil_img.copy()
    draw = ImageDraw.Draw(img)

    def draw_box(item, color, width=8):
        bbox = item["bbox"]
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        draw.rectangle([min(xs), min(ys), max(xs), max(ys)], outline=color, width=width)

    for banner in ocr_blocks["filtered_banners"]:
        draw_box(banner, BANNER_COLOR)
    for name in ocr_blocks["name_candidates"]:
        draw_box(name, NAME_COLOR)
    for tag in ocr_blocks["price_tags"]:
        draw_box(tag, PRICE_COLOR, width=10)

    return img


def _img_to_base64(pil_img, max_dim=1100, quality=85):
    """브라우저 표시용으로 적당히 축소 후 base64 JPEG 인코딩 (원본 그대로 보내면 너무 느림)"""
    img = pil_img.copy()
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


@app.post("/api/rematch")
async def rematch(text: str = Form(...)):
    """OCR/이미지 재분석 없이, 사람이 수정한 텍스트를 카탈로그와 바로 재매칭.
    2026.07.27 추가 — 인식된 텍스트를 데모 화면에서 직접 편집해 재매칭해볼 수
    있게 하기 위함 (예: OCR이 깨뜨린 텍스트를 정답으로 고쳐서 매칭 로직만 검증)."""
    result = match_catalog_text(text)
    return JSONResponse(result)
@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    corner_type: str = Form("냉장"),
    layout_type: str = Form("A"),
):
    contents = await file.read()
    img = Image.open(io.BytesIO(contents))
    # 📱 휴대폰 카메라로 세로로 찍은 사진은 픽셀은 눕혀 저장하고 EXIF Orientation
    # 태그로만 "이렇게 돌려서 보여줘"라고 표시하는 경우가 많음.
    # PIL은 이 태그를 무시하고 그냥 로드하므로, YOLO/OCR에 넘기기 전에
    # 반드시 실제 픽셀을 회전시켜서 사람이 보는 방향과 맞춰준다.
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")

    yolo_results = detect_products(img)
    ocr_results = extract_price(img)
    sku_results = match_sku(yolo_results, ocr_results, layout_type=layout_type, image_size=img.size)

    annotated = _draw_annotations(img, ocr_results["_blocks"])

    return JSONResponse({
        "corner_type": corner_type,
        "layout_type": layout_type,
        "image_size": list(img.size),
        "yolo_count": len(yolo_results),
        "debug_yolo_labels": [d["label"] for d in yolo_results[:15]],  # 진단용 — 실제 어떤 라벨로 잡히는지 확인
        "price_tag_count": len(ocr_results["_blocks"]["price_tags"]),
        "name_candidate_count": len(ocr_results["_blocks"]["name_candidates"]),
        "banner_count": len(ocr_results["_blocks"]["filtered_banners"]),
        "debug_total_raw_blocks": ocr_results.get("debug_total_raw_blocks", 0),
        "sku_results": sku_results,
        "annotated_image_base64": _img_to_base64(annotated),
    })


HTML_PAGE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>MarketPro AI Lite - 로컬 데모</title>
<style>
  :root {
    --green: #16a34a;
    --blue: #0e6eE6;
    --red: #d21313;
    --gray-bg: #f7f7f8;
    --border: #e2e2e4;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
    background: var(--gray-bg);
    margin: 0;
    padding: 32px 16px 80px;
    color: #1c1c1e;
  }
  .wrap { max-width: 960px; margin: 0 auto; }
  h1 { font-size: 22px; margin-bottom: 4px; }
  .subtitle { color: #666; font-size: 14px; margin-bottom: 28px; }

  .card {
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 20px;
  }

  .row { display: flex; gap: 24px; flex-wrap: wrap; }
  .field { flex: 1; min-width: 160px; }
  label { display: block; font-size: 13px; color: #555; margin-bottom: 6px; font-weight: 600; }

  select, input[type=file] {
    width: 100%;
    padding: 9px 10px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 14px;
    background: #fff;
  }

  #dropzone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 22px;
    text-align: center;
    color: #888;
    font-size: 13px;
    cursor: pointer;
    transition: border-color .15s;
  }
  #dropzone.dragover { border-color: var(--blue); color: var(--blue); }

  #previewWrap { margin-top: 16px; display: none; text-align: center; }
  #previewImg { max-width: 100%; max-height: 420px; border-radius: 10px; border: 1px solid var(--border); }

  button#analyzeBtn {
    margin-top: 18px;
    width: 100%;
    padding: 13px;
    font-size: 15px;
    font-weight: 700;
    color: #fff;
    background: #111;
    border: none;
    border-radius: 10px;
    cursor: pointer;
  }
  button#analyzeBtn:disabled { background: #aaa; cursor: not-allowed; }

  #status { margin-top: 12px; font-size: 13px; color: #666; text-align: center; min-height: 18px; }

  .legend { display: flex; gap: 18px; font-size: 12px; margin-bottom: 14px; flex-wrap: wrap; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }

  .stat-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
  .stat {
    flex: 1; min-width: 120px;
    background: var(--gray-bg);
    border-radius: 10px;
    padding: 12px 14px;
  }
  .stat .num { font-size: 20px; font-weight: 700; }
  .stat .label { font-size: 12px; color: #777; margin-top: 2px; }

  #annotatedImg { max-width: 100%; border-radius: 10px; border: 1px solid var(--border); }

  table { width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 13px; }
  th, td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--border); }
  th { color: #666; font-weight: 600; font-size: 12px; }
  .badge-ok { color: var(--green); font-weight: 700; }
  .badge-fail { color: #999; }

  #resultSection { display: none; }
</style>
</head>
<body>
<div class="wrap">
  <h1>MarketPro AI Lite — 로컬 데모</h1>
  <div class="subtitle">매대 사진 업로드 → YOLO 탐지 + OCR 가격표 인식 + SKU 매칭까지 한 번에 확인</div>

  <div class="card">
    <div id="dropzone">
      이미지를 드래그하거나 클릭해서 선택하세요 (JPG/PNG)
      <input type="file" id="fileInput" accept="image/*" style="display:none">
    </div>
    <div id="previewWrap">
      <img id="previewImg">
    </div>

    <div class="row" style="margin-top:18px;">
      <div class="field">
        <label>코너 종류 (corner_type)</label>
        <select id="cornerType">
          <option value="상온">상온</option>
          <option value="냉장">냉장</option>
          <option value="본매대">본매대</option>
          <option value="엔드매대">엔드매대</option>
        </select>
      </div>
      <div class="field">
        <label>매대 배치 (layout_type)</label>
        <select id="layoutType">
          <option value="A">A — 평선반형</option>
          <option value="B">B — 바구니형</option>
        </select>
      </div>
    </div>

    <button id="analyzeBtn" disabled>이미지를 먼저 선택하세요</button>
    <div id="status"></div>
  </div>

  <div class="card" id="resultSection">
    <div class="legend">
      <span><span class="swatch" style="background:#16a34a"></span> 가격표로 인식</span>
      <span><span class="swatch" style="background:#0e6eE6"></span> 상품명 후보</span>
      <span><span class="swatch" style="background:#d21313"></span> 대형 배너(제외됨)</span>
    </div>

    <div class="stat-row">
      <div class="stat"><div class="num" id="statYolo">-</div><div class="label">YOLO 탐지 객체</div></div>
      <div class="stat"><div class="num" id="statPrice">-</div><div class="label">가격표 인식</div></div>
      <div class="stat"><div class="num" id="statMatched">-</div><div class="label">SKU 매칭 성공</div></div>
      <div class="stat"><div class="num" id="statBanner">-</div><div class="label">배너 필터링</div></div>
      <div class="stat"><div class="num" id="statNameCand">-</div><div class="label">상품명 후보 인식</div></div>
      <div class="stat"><div class="num" id="statRawOcr">-</div><div class="label">OCR 원시 텍스트 블록 (디버그)</div></div>
    </div>

    <div id="yoloLabelsBox" style="font-size:12px; color:#666; margin-bottom:14px;"></div>

    <img id="annotatedImg">

    <table>
      <thead>
        <tr>
          <th>가격</th>
          <th>가격구분</th>
          <th>인식된 주변 텍스트</th>
          <th>매칭 결과</th>
          <th>점수</th>
          <th>페이싱<br><span style="font-weight:400; font-size:10px; color:#999;">(AI 미지원, 수동입력)</span></th>
          <th>디버그: 인접 거리(px)</th>
          <th>디버그: ROI 후보 수</th>
        </tr>
      </thead>
      <tbody id="resultTableBody"></tbody>
    </table>
    <button id="addMissingBtn" type="button"
            style="margin-top:14px; font-size:13px; padding:9px 14px; border-radius:8px; border:1px dashed var(--border); background:#fafafa; cursor:pointer; color:#555;">
      + 누락 제품 추가 (사진에서 가려진 가격표 등)
    </button>
  </div>
</div>

<script>
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const previewWrap = document.getElementById('previewWrap');
const previewImg = document.getElementById('previewImg');
const analyzeBtn = document.getElementById('analyzeBtn');
const statusEl = document.getElementById('status');
const resultSection = document.getElementById('resultSection');

let selectedFile = null;

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) handleFile(e.target.files[0]);
});

function handleFile(file) {
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewWrap.style.display = 'block';
  };
  reader.readAsDataURL(file);

  analyzeBtn.disabled = false;
  analyzeBtn.textContent = '분석하기';
  resultSection.style.display = 'none';
  statusEl.textContent = '';
}

analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = '분석 중... (첫 실행은 다소 걸릴 수 있습니다)';
  statusEl.textContent = 'YOLO → OCR → SKU 매칭 실행 중';
  resultSection.style.display = 'none';

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('corner_type', document.getElementById('cornerType').value);
  formData.append('layout_type', document.getElementById('layoutType').value);

  try {
    const res = await fetch('/api/analyze', { method: 'POST', body: formData });
    if (!res.ok) throw new Error('서버 오류: ' + res.status);
    const data = await res.json();
    renderResult(data);
    statusEl.textContent = '완료';
  } catch (err) {
    statusEl.textContent = '오류 발생: ' + err.message;
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = '다시 분석하기';
  }
});

function renderResult(data) {
  document.getElementById('statYolo').textContent = data.yolo_count;
  document.getElementById('statPrice').textContent = data.price_tag_count;
  document.getElementById('statBanner').textContent = data.banner_count;
  document.getElementById('statNameCand').textContent = data.name_candidate_count;
  document.getElementById('statRawOcr').textContent = data.debug_total_raw_blocks;

  const yoloLabelsBox = document.getElementById('yoloLabelsBox');
  const labels = data.debug_yolo_labels || [];
  yoloLabelsBox.textContent = labels.length
    ? ('YOLO 탐지 라벨(참고용, 상품명 아님): ' + labels.join(', '))
    : 'YOLO 탐지 라벨 없음';

  const matched = data.sku_results.filter(r => r.predicted_sku).length;
  document.getElementById('statMatched').textContent = matched + ' / ' + data.sku_results.length;

  document.getElementById('annotatedImg').src = 'data:image/jpeg;base64,' + data.annotated_image_base64;

  const tbody = document.getElementById('resultTableBody');
  tbody.innerHTML = '';
  data.sku_results.forEach((r) => {
    const tr = document.createElement('tr');
    const matchCellHtml = r.predicted_sku
      ? `<span class="badge-ok">✓ ${r.predicted_sku}</span> <span style="color:#888">(${r.brand}, ${r.spec})</span>`
      : `<span class="badge-fail">매칭 실패</span>`;
    const nearestTag = (r.debug_nearest_tag_distance != null) ? r.debug_nearest_tag_distance : '-';
    const nearbyList = (r.debug_nearby_candidate_distances || []).join(', ') || '-';
    const roiRaw = (r.debug_roi_raw_count != null) ? r.debug_roi_raw_count : '-';
    const roiAfterQuality = (r.debug_roi_after_quality_count != null) ? r.debug_roi_after_quality_count : '-';
    const priceTier = r.price_tier || '-';
    const safeText = (r.matched_name_text || '').replace(/"/g, '&quot;');
    tr.innerHTML = `
      <td>${r.price_text}</td>
      <td>${priceTier}</td>
      <td style="max-width:220px;">
        <input type="text" class="editText" value="${safeText}"
               style="width:100%; font-size:12px; padding:5px 6px; border:1px solid var(--border); border-radius:6px; box-sizing:border-box;">
        <button class="rematchBtn" type="button"
                style="margin-top:5px; font-size:11px; padding:4px 9px; border-radius:6px; border:1px solid var(--border); background:#f5f5f5; cursor:pointer;">
          ↻ 재매칭
        </button>
      </td>
      <td class="matchCell">${matchCellHtml}</td>
      <td class="scoreCell">${r.match_score}</td>
      <td>
        <input type="number" min="0" class="editFacing" value="${r.facing_count || 0}"
               style="width:52px; font-size:12px; padding:5px 6px; border:1px solid var(--border); border-radius:6px; text-align:center;">
      </td>
      <td style="font-size:11px; color:#888; max-width:180px;">옆 가격표까지 ${nearestTag}px<br>후보거리: ${nearbyList}</td>
      <td style="font-size:11px; color:#888;">ROI 안: ${roiRaw}개<br>품질필터 후: ${roiAfterQuality}개</td>
    `;
    tbody.appendChild(tr);
    wireRematchButton(tr.querySelector('.rematchBtn'));
  });

  resultSection.style.display = 'block';
}

// 재매칭 버튼 — OCR/이미지 재분석 없이, 편집한 텍스트만으로 카탈로그 재매칭.
// (2026.07.27 추가: 인식 텍스트를 사람이 고쳐서 매칭 로직만 바로 검증할 때 사용.
//  같은 <tr> 안의 .editText/.matchCell/.scoreCell을 찾아 갱신하므로, 분석 결과
//  행이든 아래 '누락 제품 추가'로 만든 새 행이든 동일하게 동작한다.)
function wireRematchButton(btn) {
  btn.addEventListener('click', async () => {
    const tr = btn.closest('tr');
    const input = tr.querySelector('.editText');
    const text = input.value;
    const matchCellEl = tr.querySelector('.matchCell');
    const scoreCellEl = tr.querySelector('.scoreCell');

    btn.disabled = true;
    const originalLabel = btn.textContent;
    btn.textContent = '...';
    try {
      const formData = new FormData();
      formData.append('text', text);
      const res = await fetch('/api/rematch', { method: 'POST', body: formData });
      if (!res.ok) throw new Error('서버 오류: ' + res.status);
      const result = await res.json();
      matchCellEl.innerHTML = result.predicted_sku
        ? `<span class="badge-ok">✓ ${result.predicted_sku}</span> <span style="color:#888">(${result.brand || '-'}, ${result.spec || '-'})</span>`
        : `<span class="badge-fail">매칭 실패${result.note ? ' — ' + result.note : ''}</span>`;
      scoreCellEl.textContent = result.match_score;
    } catch (err) {
      matchCellEl.innerHTML = `<span class="badge-fail">재매칭 오류: ${err.message}</span>`;
    } finally {
      btn.disabled = false;
      btn.textContent = originalLabel;
    }
  });
}

// 누락 제품 추가 — 사진에서 가격표 자체가 가려져 OCR이 아예 못 잡은 경우,
// 빈 행을 하나 만들어서 사람이 직접 인식 텍스트(및 가격)를 입력하고
// 재매칭해볼 수 있게 함. (2026.07.27 추가)
document.getElementById('addMissingBtn').addEventListener('click', () => {
  const tbody = document.getElementById('resultTableBody');
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>
      <input type="text" class="editPriceText" placeholder="예: 6,600"
             style="width:80px; font-size:12px; padding:5px 6px; border:1px solid var(--border); border-radius:6px; box-sizing:border-box;">
    </td>
    <td>-</td>
    <td style="max-width:220px;">
      <input type="text" class="editText" placeholder="예: 하림 더미식 장인라면 맵싸한맛"
             style="width:100%; font-size:12px; padding:5px 6px; border:1px solid var(--border); border-radius:6px; box-sizing:border-box;">
      <button class="rematchBtn" type="button"
              style="margin-top:5px; font-size:11px; padding:4px 9px; border-radius:6px; border:1px solid var(--border); background:#f5f5f5; cursor:pointer;">
        ↻ 재매칭
      </button>
    </td>
    <td class="matchCell"><span class="badge-fail">-</span></td>
    <td class="scoreCell">-</td>
    <td>
      <input type="number" min="0" class="editFacing" value="0"
             style="width:52px; font-size:12px; padding:5px 6px; border:1px solid var(--border); border-radius:6px; text-align:center;">
    </td>
    <td style="font-size:11px; color:#888;">수동 추가 (사진에서 가려짐 등)</td>
    <td>-</td>
  `;
  tbody.appendChild(tr);
  wireRematchButton(tr.querySelector('.rematchBtn'));
  tr.querySelector('.editText').focus();
  // 결과 섹션이 아직 안 열려있으면(분석 전에 먼저 누른 경우) 열어준다
  document.getElementById('resultSection').style.display = 'block';
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_app:app", host="127.0.0.1", port=8010, reload=False)
