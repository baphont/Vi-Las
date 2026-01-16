<<<<<<< Updated upstream
尾幀擷取，不需要另外使用其他工具就能輕鬆找到要的那張，支援多選一次導出  

使用場景：AI影片生成等等  
使用說明：直接使用python執行或是下載[exe](https://drive.google.com/file/d/1gkMfHIGQtZiiHUHyLMuLkeaMTN4CJfkK/view?usp=drive_link)


exe版本可能會有作業系統警告
=======
簡單的影片幀擷取工具，可以快速提取影片的最後幾幀並儲存為圖片  
支援拖曳檔案、多選擷取、排序功能等  
應用場合：製作動態背景素材、影片分析、關鍵幀提取等等  
可直接使用 python 執行，也可下載 [exe](https://drive.google.com/file/d/1XHepGLBagBd83jGxiEf0-jvElWcpCOm-/view?usp=drive_link) 檔案  
exe 檔案可能會有系統警告跳出  

不建議處理超過30秒的影片，一般幀擷取也不會到那麼長，如需處理長片建議使用專業影片工具  
目前有GPU加速，但本身沒有AMD跟INTEL卡可以測試，如果崩潰請告知  

---

## 安裝說明

### Python 環境安裝

如果您想從原始碼執行，請先安裝 Python 3.8+ 然後安裝所需套件：

```bash
pip install -r requirements.txt
```

### 手動安裝套件

如果 requirements.txt 無法正常安裝，可以手動安裝：

```bash
pip install opencv-python-headless>=4.7.0
pip install PySide6>=6.5.0
```

### 執行程式

安裝完成後，可以執行以下命令啟動程式：

```bash
python Vi-Las.py
```

### 注意事項

- 建議使用虛擬環境 (venv) 來避免套件衝突
- 支援拖曳影片檔案到視窗內直接處理
- 輸出圖檔會以幀數自動命名 (frame_XXX.jpg)
- 若有問題可從右上連結詢問
>>>>>>> Stashed changes
