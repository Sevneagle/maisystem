import os
import json
import math
import random
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk

# ==========================================
# 0. 全局配置与文件路径初始化
# ==========================================
ADMIN_ID = "114514"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, "admin")
PLAYER_DIR = os.path.join(BASE_DIR, "players")
COVER_DIR = os.path.join(BASE_DIR, "cover")
JSON_FILE = os.path.join(BASE_DIR, "maidata.json")

for directory in [ADMIN_DIR, PLAYER_DIR, COVER_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

VISITORS_FILE = os.path.join(ADMIN_DIR, "admin_visitors.txt")

song_database = {}
flattened_songs = []  # 扁平化数据：每首乐曲的每个难度单独作为一条记录

diff_mapper = {
    "Basic": ["dx_lev_bas", "lev_bas"],
    "Advanced": ["dx_lev_adv", "lev_adv"],
    "Expert": ["dx_lev_exp", "lev_exp"],
    "Master": ["dx_lev_mas", "lev_mas"],
    "Re:Master": ["dx_lev_remas", "lev_remas"]
}

# ==========================================
# 1. 核心算法与数据处理模块
# ==========================================
def parse_level_to_constant(level_str):
    """将带有+号的等级字符串转换为数字定数"""
    if not level_str:
        return 0.0
    level_str = str(level_str).strip()
    if level_str.endswith('+'):
        try:
            return float(level_str[:-1]) + 0.7
        except ValueError:
            return 0.0
    else:
        try:
            return float(level_str)
        except ValueError:
            return 0.0

def load_song_database():
    """加载JSON曲库并展开难度"""
    global song_database, flattened_songs
    if not os.path.exists(JSON_FILE):
        return
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        song_database.clear()
        flattened_songs.clear()
        
        for song in raw_data:
            title = song.get("title", "Unknown")
            category = song.get("category", "Unknown")
            display_name = f"{title} [{category}]"
            song_database[display_name] = song
            
            # 将每个存在的难度展开为独立记录
            for diff_name, fields in diff_mapper.items():
                lev_str = ""
                for field in fields:
                    if field in song:
                        lev_str = song[field]
                        break
                if lev_str:
                    constant = parse_level_to_constant(lev_str)
                    flattened_songs.append({
                        "display_name": display_name,
                        "title": title,
                        "category": category,
                        "difficulty": diff_name,
                        "level": lev_str,
                        "constant": constant
                    })
    except Exception as e:
        print(f"读取曲库失败: {e}")

def calculate_rating_details(score, constant):
    """(核心优化) 依据官方计算公式推演 Rating，单曲成绩精确到0.0000%"""
    if score >= 100.5000:
        rank, coeff = "SSS+", 22.4
    elif score >= 100.4999:
        rank, coeff = "SSS", 22.2
    elif score >= 100.0000:
        rank, coeff = "SSS", 21.6
    elif score >= 99.9999:
        rank, coeff = "SS+", 21.4
    elif score >= 99.5000:
        rank, coeff = "SS+", 21.1
    elif score >= 99.0000:
        rank, coeff = "SS", 20.8
    elif score >= 98.0000:
        rank, coeff = "S+", 20.3
    elif score >= 97.0000:
        rank, coeff = "S", 20.0
    elif score >= 94.0000:
        rank, coeff = "AAA", 16.8
    elif score >= 90.0000:
        rank, coeff = "AA", 15.2
    elif score >= 80.0000:
        rank, coeff = "A", 13.6
    else:
        rank, coeff = "B", 10.0

    # Rating计算基准：超过100.5的达成率在公式内按100.5锁定
    calc_score = min(score, 100.5) / 100.0
    rating = math.floor(constant * coeff * calc_score)
    return rank, coeff, rating

def generate_new_id():
    existing_ids = []
    if os.path.exists(VISITORS_FILE):
        with open(VISITORS_FILE, "r", encoding="utf-8") as f:
            existing_ids = [line.strip() for line in f.readlines()]
    while True:
        new_id = f"DX_{random.randint(1000, 9999)}"
        if new_id not in existing_ids:
            break
    with open(VISITORS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{new_id}\n")
    return new_id

def is_valid_player_id(player_id):
    if not os.path.exists(VISITORS_FILE):
        return False
    with open(VISITORS_FILE, "r", encoding="utf-8") as f:
        valid_ids = [line.strip() for line in f.readlines()]
    return player_id in valid_ids

def submit_game_score(player_id, display_name, difficulty, score):
    """提交成绩并重新对 Best 50 排序存储"""
    txt1_path = os.path.join(PLAYER_DIR, f"{player_id}_txt1.txt")
    txt2_path = os.path.join(PLAYER_DIR, f"{player_id}_txt2.txt")

    # 读取已有记录
    all_records = {}
    if os.path.exists(txt1_path):
        with open(txt1_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3:
                    key = f"{parts[0]}||{parts[1]}"
                    all_records[key] = float(parts[2].replace("%", ""))

    current_key = f"{display_name}||{difficulty}"
    if current_key not in all_records or score > all_records[current_key]:
        all_records[current_key] = score

    # 重新计算 Rating
    calculated_list = []
    with open(txt1_path, "w", encoding="utf-8") as f:
        for key, s_score in all_records.items():
            d_name, diff = key.split("||")
            f.write(f"{d_name}|{diff}|{s_score:.4f}%\n")
            
            song_info = song_database.get(d_name, {})
            lev_str = ""
            for field in diff_mapper.get(diff, []):
                if field in song_info:
                    lev_str = song_info[field]; break
            
            constant = parse_level_to_constant(lev_str)
            _, _, rating = calculate_rating_details(s_score, constant)
            calculated_list.append((d_name, diff, s_score, rating))

    # 取最高的前50首
    calculated_list.sort(key=lambda x: x[3], reverse=True)
    best_50 = calculated_list[:50]

    with open(txt2_path, "w", encoding="utf-8") as f:
        for d_name, diff, s_score, rating in best_50:
            f.write(f"{d_name}|{diff}|{s_score:.4f}%|{rating}\n")

def read_player_b50(player_id):
    """读取 Best 50 数据"""
    txt2_path = os.path.join(PLAYER_DIR, f"{player_id}_txt2.txt")
    if not os.path.exists(txt2_path):
        return []
    records = []
    with open(txt2_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) == 4:
                records.append({
                    "display_name": parts[0],
                    "difficulty": parts[1],
                    "score": float(parts[2].replace("%", "")),
                    "rating": int(parts[3])
                })
    return records

def get_cover_image(display_name, target_size=(75, 75)):
    song_info = song_database.get(display_name, {})
    img_filename = song_info.get("image_file")
    if img_filename:
        img_path = os.path.join(COVER_DIR, img_filename)
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img = img.resize(target_size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            except: pass
    return None

# ==========================================
# 2. UI 视图表现层 (Tkinter)
# ==========================================
class MaimaiSystemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("舞萌dx成绩管理系统Eagle114514")
        self.root.geometry("500x450")
        load_song_database()

        tk.Label(root, text="舞萌dx成绩管理系统", font=("Microsoft YaHei", 18, "bold"), fg="#1296db").pack(pady=15)
        tk.Label(root, text=f"本地曲库已加载: {len(song_database)} 首歌 | {len(flattened_songs)} 个谱面", font=("Microsoft YaHei", 9), fg="gray").pack(pady=2)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=25)

        tk.Button(btn_frame, text="🔒 管理员登录", font=("Microsoft YaHei", 11), width=20, command=self.pop_admin_login).grid(row=0, column=0, pady=8)
        tk.Button(btn_frame, text="👤 玩家凭证登录", font=("Microsoft YaHei", 11), width=20, command=self.pop_player_login).grid(row=1, column=0, pady=8)
        tk.Button(btn_frame, text="🔑 获取新玩家ID", font=("Microsoft YaHei", 11), width=20, bg="#e6f7ff", fg="#1890ff", command=self.action_get_new_id).grid(row=2, column=0, pady=8)
        tk.Button(btn_frame, text="🌐 游客直接试玩", font=("Microsoft YaHei", 11), width=20, bg="#f6ffed", fg="#52c41a", command=self.open_visitor_panel).grid(row=3, column=0, pady=8)

    def pop_admin_login(self):
        login_win = tk.Toplevel(self.root)
        login_win.geometry("300x150")
        tk.Label(login_win, text="请输入管理员ID:").pack(pady=15)
        id_entry = tk.Entry(login_win, show="*")
        id_entry.pack()

        def do_admin_login():
            admin_id_input = id_entry.get().strip() # 1. 先获取值
            if admin_id_input == ADMIN_ID:
                login_win.destroy()                 # 2. 再销毁窗口
                self.open_admin_panel()             # 3. 最后打开新页面
            else:
                messagebox.showerror("错误", "认证失败")

        tk.Button(login_win, text="登录", command=do_admin_login).pack(pady=15)

    def pop_player_login(self):
        login_win = tk.Toplevel(self.root)
        login_win.geometry("300x150")
        tk.Label(login_win, text="请输入玩家ID:").pack(pady=15)
        id_entry = tk.Entry(login_win)
        id_entry.pack()

        def do_player_login():
            p_id = id_entry.get().strip()          # 1. 先获取值
            if is_valid_player_id(p_id):
                login_win.destroy()                # 2. 再销毁窗口
                self.open_player_panel(p_id)       # 3. 最后打开新页面
            else:
                messagebox.showerror("错误", "凭证不存在")

        tk.Button(login_win, text="登录", command=do_player_login).pack(pady=15)
    def action_get_new_id(self):
        messagebox.showinfo("成功", f"新ID分发成功:\n\n{generate_new_id()}")

    def open_admin_panel(self):
        admin_win = tk.Toplevel(self.root)
        admin_win.title("后台数据中心")
        admin_win.geometry("400x300")
        tk.Label(admin_win, text="曲库概要信息(只读)", font=("Microsoft YaHei", 12)).pack(pady=10)
        lb = tk.Listbox(admin_win, width=50)
        lb.pack(pady=10)
        for s in list(song_database.keys())[:50]:
            lb.insert(tk.END, s)
        if len(song_database) > 50:
            lb.insert(tk.END, "...(仅展示前50首)")

    def build_song_selector(self, parent):
        """核心选歌列表过滤组件"""
        filter_frame = tk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(filter_frame, text="分类:").pack(side=tk.LEFT, padx=2)
        cat_combo = ttk.Combobox(filter_frame, values=["全部", "流行&动漫", "niconico＆VOCALOID™", "东方Project", "其他游戏", "舞萌", "音击/中二节奏"], state="readonly", width=14)
        cat_combo.current(0)
        cat_combo.pack(side=tk.LEFT, padx=2)
        
        tk.Label(filter_frame, text="等级:").pack(side=tk.LEFT, padx=2)
        lev_combo = ttk.Combobox(filter_frame, values=["全部", "10", "11", "12", "13", "14", "15"], state="readonly", width=5)
        lev_combo.current(0)
        lev_combo.pack(side=tk.LEFT, padx=2)
        
        tk.Label(filter_frame, text="排序:").pack(side=tk.LEFT, padx=2)
        sort_combo = ttk.Combobox(filter_frame, values=["默认", "定数降序", "定数升序"], state="readonly", width=8)
        sort_combo.current(0)
        sort_combo.pack(side=tk.LEFT, padx=2)
        
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("title", "category", "difficulty", "level", "constant")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        tree.heading("title", text="歌名"); tree.column("title", width=160, anchor="w")
        tree.heading("category", text="分类"); tree.column("category", width=100, anchor="w")
        tree.heading("difficulty", text="难度"); tree.column("difficulty", width=80, anchor="center")
        tree.heading("level", text="等级"); tree.column("level", width=50, anchor="center")
        tree.heading("constant", text="定数"); tree.column("constant", width=50, anchor="center")
        
        scroll = tk.Scrollbar(tree_frame, command=tree.yview)
        tree.config(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def update_treeview(*args):
            cat, lvl, srt = cat_combo.get(), lev_combo.get(), sort_combo.get()
            filtered = [s for s in flattened_songs if (cat == "全部" or s["category"] == cat) and (lvl == "全部" or s["level"].startswith(lvl))]
            
            if srt == "定数降序": filtered.sort(key=lambda x: x["constant"], reverse=True)
            elif srt == "定数升序": filtered.sort(key=lambda x: x["constant"])
                
            tree.delete(*tree.get_children())
            for s in filtered:
                tree.insert("", tk.END, values=(s["title"], s["category"], s["difficulty"], s["level"], f"{s['constant']:.1f}"), iid=f"{s['display_name']}||{s['difficulty']}")

        for combo in [cat_combo, lev_combo, sort_combo]:
            combo.bind("<<ComboboxSelected>>", update_treeview)
        
        update_treeview()
        return tree

    def open_player_panel(self, player_id):
        player_win = tk.Toplevel(self.root)
        player_win.title(f"玩家主控台 - {player_id}")
        player_win.geometry("600x650")

        notebook = ttk.Notebook(player_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: 录入
        play_tab = tk.Frame(notebook)
        notebook.add(play_tab, text="🎮 成绩录入结算")
        
        tree = self.build_song_selector(play_tab)

        # 选中展示区域
        info_frame = tk.Frame(play_tab)
        info_frame.pack(fill=tk.X, pady=5)
        
        cover_label = tk.Label(info_frame, text="[暂无封面]", width=10, height=5, bg="#e0e0e0")
        cover_label.pack(side=tk.LEFT, padx=10)
        
        sel_label = tk.Label(info_frame, text="请在上方列表中点击选中一首谱面", font=("Microsoft YaHei", 10, "bold"), fg="#1296db")
        sel_label.pack(side=tk.LEFT, padx=10)
        
        selected_data = {"d_name": None, "diff": None}

        def on_tree_select(event):
            selected = tree.selection()
            if not selected: return
            iid = selected[0]
            display_name, difficulty = iid.split("||")
            selected_data["d_name"] = display_name
            selected_data["diff"] = difficulty
            
            photo = get_cover_image(display_name, (80, 80))
            if photo:
                cover_label.config(image=photo, text=""); cover_label.image = photo
            else:
                cover_label.config(image="", text="[无封面]")
            
            item = tree.item(iid)
            sel_label.config(text=f"当前锁定:\n{item['values'][0]} ({difficulty})\n等级: {item['values'][3]}  |  定数: {item['values'][4]}")

        tree.bind("<<TreeviewSelect>>", on_tree_select)

        # 结算区域
        score_frame = tk.Frame(play_tab)
        score_frame.pack(fill=tk.X, pady=10)
        tk.Label(score_frame, text="达成率(0-101):").pack(side=tk.LEFT, padx=5)
        score_entry = tk.Entry(score_frame, width=12)
        score_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(score_frame, text="% (精确到0.0000)").pack(side=tk.LEFT)

        def commit():
            if not selected_data["d_name"]:
                messagebox.showwarning("提示", "请先在列表中选中一首歌！")
                return
            try:
                score = float(score_entry.get())
                if not (0 <= score <= 101): raise ValueError
            except:
                messagebox.showerror("错误", "请输入有效的数字成绩")
                return

            submit_game_score(player_id, selected_data["d_name"], selected_data["diff"], score)
            messagebox.showinfo("完成", "成绩上传成功！Best 50 排行榜已重新洗牌。")
            score_entry.delete(0, tk.END)

        tk.Button(score_frame, text="结算上传", bg="#52c41a", fg="white", command=commit).pack(side=tk.RIGHT, padx=15)

        # Tab 2: Best 50 画布
        b50_tab = tk.Frame(notebook)
        notebook.add(b50_tab, text="🏆 个人 Best 50 战力图谱")

        canvas = tk.Canvas(b50_tab, borderwidth=0)
        scrollbar = tk.Scrollbar(b50_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.img_cache = []

        def render_b50_grid():
            for widget in scrollable_frame.winfo_children(): widget.destroy()
            self.img_cache.clear()

            records = read_player_b50(player_id)
            if not records:
                tk.Label(scrollable_frame, text="暂无战力数据", font=("Microsoft YaHei", 11)).pack(pady=40)
                return

            total_rating = sum([r["rating"] for r in records])
            tk.Label(scrollable_frame, text=f"🔥 Best 50 总 Rating: {total_rating} DX", font=("Microsoft YaHei", 14, "bold"), fg="#ff4d4f").grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=10)

            for idx, r in enumerate(records):
                row, col = (idx // 4) + 1, idx % 4
                card = tk.Frame(scrollable_frame, bd=1, relief="solid", padx=5, pady=5)
                card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

                photo = get_cover_image(r["display_name"], (70, 70))
                if photo:
                    img_lbl = tk.Label(card, image=photo)
                    img_lbl.pack()
                    self.img_cache.append(photo)
                
                short_title = r["display_name"].split(" [")[0]
                if len(short_title) > 8: short_title = short_title[:7] + ".."
                
                song_info = song_database.get(r["display_name"], {})
                lev_str = ""
                for field in diff_mapper.get(r["difficulty"], []):
                    if field in song_info: lev_str = song_info[field]; break
                
                rank, _, _ = calculate_rating_details(r["score"], parse_level_to_constant(lev_str))

                tk.Label(card, text=short_title, font=("Microsoft YaHei", 8, "bold")).pack()
                tk.Label(card, text=f"{r['difficulty']} ({lev_str})", font=("Arial", 8), fg="gray").pack()
                tk.Label(card, text=f"{r['score']:.4f}%", font=("Arial", 9, "bold"), fg="#2f54eb").pack()
                tk.Label(card, text=f"RT: {r['rating']} ({rank})", font=("Arial", 9, "bold"), fg="#52c41a").pack()

        notebook.bind("<<NotebookTabChanged>>", lambda e: render_b50_grid() if notebook.index(notebook.select()) == 1 else None)

    def open_visitor_panel(self):
        visitor_win = tk.Toplevel(self.root)
        visitor_win.geometry("500x500")
        tk.Label(visitor_win, text="游客单曲计算模拟器", font=("Microsoft YaHei", 12, "bold")).pack(pady=10)

        tree = self.build_song_selector(visitor_win)
        
        score_frame = tk.Frame(visitor_win)
        score_frame.pack(fill=tk.X, pady=10)
        tk.Label(score_frame, text="达成率(0-101):").pack(side=tk.LEFT, padx=5)
        se = tk.Entry(score_frame, width=12)
        se.pack(side=tk.LEFT, padx=5)

        def calc():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("提示", "请选中歌曲")
                return
            try: sc = float(se.get())
            except: return
            
            iid = selected[0]
            display_name, diff = iid.split("||")
            item = tree.item(iid)
            constant = float(item['values'][4])
            
            rank, coeff, rat = calculate_rating_details(sc, constant)
            messagebox.showinfo("模拟结算", f"谱面定数: {constant}\n计算RANK: {rank}\n计算系数: {coeff}\n\n单曲 Rating: {rat}")

        tk.Button(score_frame, text="模拟结算", command=calc, bg="#1296db", fg="white").pack(side=tk.RIGHT, padx=15)

if __name__ == "__main__":
    root = tk.Tk()
    app = MaimaiSystemApp(root)
    root.mainloop()