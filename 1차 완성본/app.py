from flask import Flask, request, render_template, redirect, url_for, send_file
from html import generate_result_html
import json
import os
import re

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.py")
JSON_PATH = os.path.join(BASE_DIR, "prefs.json")

@app.route('/')
def landing():
    return render_template('landing.html')  # 랜딩 페이지

@app.route('/index')
def index():
    return render_template('index.html')  # 카테고리 입력 페이지

@app.route('/save_prefs', methods=['POST'])
def save_prefs():
    prefs = request.get_json()

    # config.py의 prefs 딕셔너리 수정
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_text = f.read()
    except FileNotFoundError:
        return "config.py not found", 500

    new_prefs_str = f"prefs = {json.dumps(prefs, ensure_ascii=False, indent=4)}"
    config_text = re.sub(r"prefs\s*=\s*{.*?}\n", new_prefs_str + "\n", config_text, flags=re.DOTALL)

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(config_text)

    with open(JSON_PATH, 'w', encoding='utf-8') as jf:
        json.dump(prefs, jf, ensure_ascii=False, indent=4)

    return "OK"

@app.route('/save_location', methods=['POST'])
def save_location():
    coords = request.get_json()
    lat = coords.get("lat")
    lon = coords.get("lon")

    if lat is None or lon is None:
        return "Invalid coordinates", 400

    # 위도와 경도를 "lat : lon" 형식으로 저장
    new_address_line = f'current_address = "{lat} : {lon}"\n'

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_text = f.read()

        config_text = re.sub(r'current_address\s*=.*', new_address_line, config_text)

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            f.write(config_text)

        return "Location saved"

    except Exception as e:
        return str(e), 500
    
@app.route('/result')
def result():
    generate_result_html()
    return render_template("result.html")


@app.route('/config')
def config_view():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        code = f.read()
    return render_template('config_view.html', code=code)

@app.route("/update_weight", methods=["POST"])
def update_weight():
    from pathlib import Path
    from flask import jsonify
    import re

    data = request.get_json()
    subcategory = data.get("subcategory", "")

    if isinstance(subcategory, list):
        subcategory = subcategory[0] if subcategory else ""

    if not subcategory:
        return jsonify(success=False)

    config_path = Path(__file__).parent / "config.py"

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    inside_weights = False
    updated = False
    found = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # subcategory_WEIGHTS 시작
        if stripped.startswith("subcategory_WEIGHTS"):
            inside_weights = True
            new_lines.append(line)
            continue

        # 딕셔너리 내부 처리
        if inside_weights:
            if stripped == "}":
                if not found:
                    # 새로 추가
                    new_lines.append(f'    "{subcategory}": 0.2,\n')
                new_lines.append(line)
                inside_weights = False
                updated = True
                continue

            match = re.match(r'(\s*)"(.+?)"\s*:\s*([\d.]+),', line)
            if match:
                key = match.group(2)
                value = float(match.group(3))
                if key == subcategory:
                    value = round(value + 0.2, 2)
                    line = f'{match.group(1)}"{key}": {value},\n'
                    found = True
                    updated = True
            new_lines.append(line)
        else:
            new_lines.append(line)

    if updated:
        with open(config_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return jsonify(success=True)
    else:
        return jsonify(success=False)





if __name__ == '__main__':
    app.run(debug=True)
