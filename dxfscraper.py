import os
import re
import uuid
import tempfile
import pandas as pd
import ezdxf
import plotly.express as px
from flask import Flask, request, render_template_string, send_file
import html

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()

sheet_number_pattern = re.compile(r"(?:DWG\s*No\.?|Drawing|Sheet)\s*[:\-]?\s*([\w\-_.]+)", re.IGNORECASE)

HTML_FORM = '''
<!doctype html>
<html lang="en" style="height: 100%; width: 100%; margin: 0;">
<head>
  <meta charset="UTF-8">
  <title>DXF Tag Visualizer</title>
  <style>
    :root {
      --bg: #ffffff;
      --fg: #000000;
      --accent: #4a90e2;
    }
    body.dark {
      --bg: #1e1e1e;
      --fg: #f0f0f0;
      --accent: #ffa726;
    }
    html, body {
      height: 100%;
      width: 100%;
      margin: 0;
      font-family: Arial, sans-serif;
      background: var(--bg);
      color: var(--fg);
      display: flex;
      flex-direction: column;
      transition: background 0.3s ease, color 0.3s ease;
    }
    #main-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;
    }
    #form-container {
      transition: background 0.3s ease, color 0.3s ease;
      padding: 20px;
      flex-shrink: 0;
      background: var(--bg);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .drop-zone {
      border: 2px dashed var(--accent);
      padding: 20px;
      text-align: center;
      border-radius: 8px;
      transition: background 0.3s;
    }
    .drop-zone.dragover {
      background: #f0f8ff;
    }
    input[type="file"] {
      display: none;
    }
    input[type="text"] {
      margin-top: 5px;
      padding: 10px;
      border: 1px solid var(--accent);
      border-radius: 5px;
      background: var(--bg);
      color: var(--fg);
      transition: border 0.3s ease, background 0.3s ease, color 0.3s ease;
    }
    input[type="submit"], button {
      padding: 10px 20px;
      background: var(--accent);
      border: none;
      color: #fff;
      border-radius: 5px;
      cursor: pointer;
      transition: background 0.3s ease;
    }
    input[type="submit"]:hover, button:hover {
      background: #357ab8;
    }
    #plot-container {
      flex-grow: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    #plot-container > div {
      flex-grow: 1;
      height: 100%;
    }
    #download-container {
      transition: background 0.3s ease, color 0.3s ease;
      padding: 10px;
      flex-shrink: 0;
    }
    .toggle-container {
      align-self: flex-end;
      margin-bottom: 10px;
    }
  </style>
</head>
<body>
  <div id="main-container">
    <div id="form-container">
      
      <h2 style="margin: 0 0 10px 0;">Upload a DXF File</h2>
<p id="selected-file" style="margin: 0 0 10px 0;"><strong>Selected file:</strong> <span id="file-name-label">None</span></p>
      <form method="post" enctype="multipart/form-data" id="upload-form">
        <div class="drop-zone" id="drop-zone">
          <p>Drag & drop a .dxf file here or click to select one</p>
          <input type="file" name="file" id="file-input">
        </div>
        <label for="examples">Enter example tags (comma-separated):</label>
        <input type="text" name="examples" placeholder="12AB3456, 83WE0101"><br>
        <input type="submit" value="Upload">
      </form>
    </div>
    {% if plot_html %}
  <div id="plot-container">
    {{ plot_html|safe }}
  </div>
{% endif %}
<div id="download-container" style="position: fixed; bottom: 0; right: 0; display: flex; justify-content: space-between; align-items: center; padding: 10px; gap: 10px; background: var(--bg); width: 100%;">
  <div>
    {% if plot_html %}
      <a href="/download/{{ excel_filename }}" download style="margin-left: 25px;">
        <button>Download Excel</button>
      </a>
    {% endif %}
  </div>
  <div style="display: flex; gap: 10px;">
    {% if plot_html %}
      <button onclick="toggleFullscreen()" title="Expand Plot">⛶</button>
    {% endif %}
    <button onclick="toggleTheme()" title="Toggle Theme">🌓</button>
  </div>
</div>
</div>

  </div>
  <script>
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileNameLabel = document.getElementById('file-name-label');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    fileInput.files = e.dataTransfer.files;
    if (fileNameLabel) {
      fileNameLabel.textContent = e.dataTransfer.files[0].name;
    }
  }
});
    fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0 && fileNameLabel) {
      fileNameLabel.textContent = fileInput.files[0].name;
    }
  });
    function toggleTheme() {
    const isDark = document.body.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  }

  window.onload = () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      document.body.classList.add('dark');
    }
  };
    const observer = new MutationObserver(() => {
    const plotDiv = document.getElementById('plotly-div');
    if (plotDiv) {
  const isDark = document.body.classList.contains('dark');
  const updateColor = 'white';
  plotDiv.style.backgroundColor = updateColor;
  const plotCanvas = plotDiv.querySelector('.plotly');
  if (plotCanvas) {
    plotCanvas.style.backgroundColor = updateColor;
    const paper = plotCanvas.querySelector('.bg');
    if (paper) paper.style.fill = updateColor;
  }
}
  });
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
function toggleFullscreen() {
  const plot = document.getElementById('plotly-div');
  if (plot.requestFullscreen) {
    plot.requestFullscreen();
  } else if (plot.webkitRequestFullscreen) {
    plot.webkitRequestFullscreen();
  } else if (plot.msRequestFullscreen) {
    plot.msRequestFullscreen();
  }
}
</script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    plot_html = None
    excel_filename = None
    if request.method == 'POST':
        file = request.files['file']
        example_tags = request.form.get('examples', '')
        if file and file.filename.lower().endswith('.dxf'):
            file_id = uuid.uuid4().hex
            filename = f"{file_id}.dxf"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            excel_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.xlsx")
            regex_patterns = []
            for tag in example_tags.split(','):
                tag = tag.strip()
                if tag:
                    tag_pattern = ''.join([r"\d" if c.isdigit() else r"[A-Za-z]" if c.isalpha() else re.escape(c) for c in tag])
                    regex_patterns.append(re.compile(rf"\b{tag_pattern}\b"))
            if not regex_patterns:
                regex_patterns = [re.compile(r"\b\d{2}[A-Za-z]{2}\d{4}\b")]
            plot_html = generate_plot(filepath, excel_path, regex_patterns)
            os.remove(filepath)
            excel_filename = os.path.basename(excel_path)
    return render_template_string(HTML_FORM, plot_html=plot_html, excel_filename=excel_filename, uploaded_filename=file.filename if request.method == 'POST' and 'file' in request.files else None)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(file_path, as_attachment=True)

def generate_plot(dxf_path, excel_output_path, regex_patterns):
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        return f"<p>Error reading DXF: {e}</p>"

    rows, sheet_outlines = [], []
    layout_drawing_number = {}

    for layout in doc.layouts:
        if layout.name.lower() == "model":
            continue
        for e in layout.query("TEXT MTEXT"):
            text = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
            match = sheet_number_pattern.search(text)
            if match:
                layout_drawing_number[layout.name] = match.group(1).strip()
                break
        else:
            layout_drawing_number[layout.name] = layout.name

    for layout in doc.layouts:
        if layout.name.lower() == "model":
            continue
        max_area, best_vp = 0, None
        for vp in layout.query("VIEWPORT"):
            try:
                vc = vp.dxf.view_center_point
                vh = vp.dxf.view_height
                pw = getattr(vp.dxf, "width", 1.0)
                ph = getattr(vp.dxf, "height", 1.0)
                ar = pw / ph if ph != 0 else 1.0
                vw = vh * ar
                area = vw * vh
                if area > max_area:
                    max_area = area
                    best_vp = (vc, vw, vh)
            except Exception:
                continue
        if best_vp:
            vc, vw, vh = best_vp
            x1, y1 = vc[0] - vw / 2, vc[1] - vh / 2
            x2, y2 = vc[0] + vw / 2, vc[1] + vh / 2
            sheet_outlines.append({
                "Drawing": layout_drawing_number[layout.name],
                "X1": x1, "Y1": y1, "X2": x2, "Y2": y2
            })

    msp = doc.modelspace()
    tag_found = False
    for e in msp.query("TEXT MTEXT"):
        text = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
        if not text:
            continue
        insert = e.dxf.insert
        x, y = insert.x, insert.y
        for pattern in regex_patterns:
            matches = pattern.findall(text)
            if matches:
                tag_found = True
                for tag in matches:
                    device_type = tag[2:4] if len(tag) >= 4 else "XX"
                    matched_drawing = "UNPLACED"
                    for outline in sheet_outlines:
                        if outline["X1"] <= x <= outline["X2"] and outline["Y1"] <= y <= outline["Y2"]:
                            matched_drawing = outline["Drawing"]
                            break
                    rows.append({"Tag": tag, "X": x, "Y": y, "Drawing": matched_drawing, "DeviceType": device_type})

    if not tag_found:
        return "<p>No tags found in the DXF.</p>"

    df = pd.DataFrame(rows).drop_duplicates()
    df.to_excel(excel_output_path, index=False, columns=["Tag", "Drawing", "DeviceType"])

    df["DeviceTypeLabel"] = df["DeviceType"] + " (" + df.groupby("DeviceType")["DeviceType"].transform("count").astype(str) + ")"

    fig = px.scatter(
        df, x="X", y="Y", text="Tag", color="DeviceTypeLabel",
        hover_data={"Tag": True, "Drawing": True, "X": False, "Y": False},
        labels={"DeviceTypeLabel": "Device Type"},
    )
    fig.update_traces(textposition='top center')

    for outline in sheet_outlines:
        fig.add_shape(
            type="rect",
            x0=outline["X1"], y0=outline["Y1"], x1=outline["X2"], y1=outline["Y2"],
            line=dict(color="Red", width=2),
        )
        fig.add_annotation(
            x=outline["X2"] - 30, y=outline["Y1"],
            text=outline["Drawing"], showarrow=False,
            font=dict(size=8, color="red"), xanchor="left", yanchor="top"
        )

    fig.update_layout(
        autosize=True,
        height=None,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_scaleanchor="x",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    html_string = fig.to_html(full_html=False, include_plotlyjs='cdn', config={"responsive": True}, div_id='plotly-div')
    return html_string

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
