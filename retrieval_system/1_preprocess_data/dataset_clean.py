input_file = "D:/RAG/xss_attacks/dataset/XSS_dataset_testing.csv"
output_file = "D:/RAG/xss_attacks/dataset/XSS_dataset_testing_cleaned.csv"

# 讀取舊的 CSV（可能是 ISO-8859-1）
with open(input_file, "r", encoding="ISO-8859-1") as f_in, open(output_file, "w", encoding="utf-8") as f_out:
    f_out.write(f_in.read())

print(f"✅ 已成功將 CSV 轉為 UTF-8，存為 {output_file}")
