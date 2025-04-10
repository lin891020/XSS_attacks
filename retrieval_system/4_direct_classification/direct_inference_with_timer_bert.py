import os
import csv
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, accuracy_score, precision_score, recall_score
import matplotlib.pyplot as plt
from tqdm import tqdm
import time

# 設置模型名稱
# model_name = "microsoft/codebert-base"  # 可替換為更適合 XSS 檢測的模型
# model_name = "jackaduma/SecBERT"
# model_name = "cssupport/mobilebert-sql-injection-detect"

model_name = "roberta-base-openai-detector"


tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

print(f"正在使用 {model_name} 模型進行 XSS 檢測...")

# 定義 XSS 風險分類函數
def classify_xss_risk(user_input):
    """
    使用 CodeBERT 模型判斷 XSS Payload 風險。
    Args:
        user_input (str): 輸入的 XSS Payload。
    Returns:
        dict: 包含判斷結果和詳細信息的字典。
    """
    start_time = time.perf_counter()

    # 進行 Tokenization 並轉為 PyTorch 張量
    inputs = tokenizer(user_input, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)

    # 計算 logits 和分類概率
    logits = outputs.logits
    probabilities = torch.nn.functional.softmax(logits, dim=-1).squeeze().tolist()

    # 判斷分類結果
    predicted_label = np.argmax(probabilities)
    label_map = {0: "benign", 1: "malicious"}  # 0 = 合法 (benign), 1 = 惡意 (malicious)

    inference_time_ms = (time.perf_counter() - start_time) * 1000  # 轉換為毫秒

    return {
        "input_payload": user_input,
        "classification": label_map[predicted_label],
        "probabilities": {label_map[0]: round(probabilities[0], 4), label_map[1]: round(probabilities[1], 4)},
        "inference_time_ms": inference_time_ms
    }

# 讀取測試數據
input_file = "D:/RAG/xss_attacks/dataset/XSS_dataset_testing_cleaned.csv"
print(f"📥 讀取測試數據: {input_file}...")
results = []
true_labels = []
predicted_labels = []

data_count = 0
with open(input_file, "r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    data = list(reader)
    data_count = len(data)
    print(f"✅ 共讀取到 {data_count} 筆 XSS 測試數據。")

# 記錄整體測試時間
start_time_total = time.time()

# 處理每筆數據
for row in tqdm(data, desc="處理測試數據進度", unit="筆"):
    user_payload = row["Payload"]
    true_label = row["Label"]

    # 判斷 XSS 風險
    result = classify_xss_risk(user_payload)

    # 定義映射
    mapped_label = {"benign": 0, "malicious": 1}

    results.append({
        "payload": user_payload,
        "true_label": int(true_label),  # 確保 true_label 為數字
        "predicted_label": mapped_label[result["classification"]],  # 轉換 predicted_label
        "probabilities": result["probabilities"],
        "inference_time_ms": result["inference_time_ms"]
    })
    true_labels.append(int(true_label))
    predicted_labels.append(mapped_label[result["classification"]])

# 記錄測試完成時間
total_time = time.time() - start_time_total
average_time = (total_time / data_count) * 1000  # 轉換為毫秒

# 過濾錯誤預測
wrong_predictions = [
    result for result in results if result["true_label"] != result["predicted_label"]
]

# 設置輸出目錄
base_output_dir = "D:/RAG/xss_attacks/result/direct"
model_output_dir = os.path.join(base_output_dir, model_name.replace('-', '_').replace('/', '_'))

# 確保資料夾存在
os.makedirs(model_output_dir, exist_ok=True)

# 設置輸出文件路徑
output_file = os.path.join(model_output_dir, f"testing_results_{model_name.replace('-', '_').replace('/', '_')}.csv")
wrong_output_file = os.path.join(model_output_dir, f"testing_results_wrong_{model_name.replace('-', '_').replace('/', '_')}.csv")
confusion_matrix_file = os.path.join(model_output_dir, f"confusion_matrix_{model_name.replace('-', '_').replace('/', '_')}.png")
summary_file = os.path.join(model_output_dir, "summary_results.txt")

# 寫入結果到 CSV
print(f"📄 寫入結果到 {output_file}...")
with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["payload", "true_label", "predicted_label", "probabilities", "inference_time_ms"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(results)

print(f"✅ 結果已保存到 {output_file}！")

# 寫入錯誤預測結果到 CSV
print(f"⚠️ 正在將錯誤預測結果寫入到 {wrong_output_file}...")
with open(wrong_output_file, "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["payload", "true_label", "predicted_label", "probabilities", "inference_time_ms"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(wrong_predictions)

print(f"⚠️ 錯誤預測結果已保存到 {wrong_output_file}！")

# 計算 Accuracy, Precision, Recall
accuracy = accuracy_score(true_labels, predicted_labels) * 100
precision = precision_score(true_labels, predicted_labels) * 100
recall = recall_score(true_labels, predicted_labels) * 100

# 計算總時間格式化
total_minutes = int(total_time // 60)
total_seconds = int(total_time % 60)

# 打印結果
print(f"📊 Accuracy: {accuracy:.3f}%")
print(f"📊 Precision: {precision:.3f}%")
print(f"📊 Recall: {recall:.3f}%")
print(f"⏱️ Total Time: {total_minutes}min {total_seconds}sec")
print(f"⏱️ Average Time: {average_time:.2f}ms")

# 繪製混淆矩陣
print("📊 繪製混淆矩陣...")
cm = confusion_matrix(true_labels, predicted_labels, labels=[0, 1])
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["benign", "malicious"])
disp.plot(cmap=plt.cm.Blues, colorbar=False, values_format='.0f')

# 設置標題與標籤
plt.title(f"Confusion Matrix_{model_name.replace('-', '_').replace('/', '_')}")
plt.xlabel("Predicted Label")
plt.ylabel("True Label")

# 保存混淆矩陣圖像
plt.savefig(confusion_matrix_file)
plt.show()

print(f"✅ 混淆矩陣已保存為：{confusion_matrix_file}")

# 生成 Summary File
print(f"📄 生成總結文件 {summary_file}...")
with open(summary_file, "w", encoding="utf-8") as f:
    f.write(f"Accuracy: {accuracy:.3f}%\n")
    f.write(f"Precision: {precision:.3f}%\n")
    f.write(f"Recall: {recall:.3f}%\n")
    f.write(f"Total Time: {total_minutes}min {total_seconds}sec\n")
    f.write(f"Average Time: {average_time:.2f}ms\n")

print(f"✅ Summary 已保存至 {summary_file}！")
