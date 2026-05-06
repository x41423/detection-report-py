import os
import json
import logging
from config import load_config, save_config
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from data_generator import (
    format_json_data,
    gen_inhibition_rates,
    parse_json_data,
    parse_vegetable_list,
    remove_duplicate_varieties,
    set_risk_lists,
    set_rate_ranges,
)
from doc_writer import process_documents
from shared.logging_utils import configure_application_logging


class PesticideApp:
    """
    滨鲜农残检测助手主应用程序类。

    提供GUI界面用于生成农残检测报告，包括蔬菜品种输入、抑制率生成、
    文档处理和配置管理。
    """
    def __init__(self, root):
        """
        初始化应用程序。

        设置窗口属性、日志、配置、样式，并调用UI设置。
        """
        self.root = root
        self.root.title("滨鲜农残检测助手 V11.0 - 像素级排版保护版")
        self.root.geometry("850x900")

        # 设置 ttk 样式以统一界面
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 使用现代主题
        self.style.configure('TButton', font=('微软雅黑', 9))
        self.style.configure('TLabel', font=('微软雅黑', 9))
        self.style.configure('TEntry', font=('微软雅黑', 10))
        self.style.configure('TLabelFrame', font=('微软雅黑', 10, 'bold'))

        # 设置日志
        configure_application_logging("legacy-desktop.log")
        logging.info("程序启动")

        # 读取配置
        self.config = load_config()
        self.path_big_root = self.config.get("big_path", "")
        self.path_small_root = self.config.get("small_path", "")
        self.path_output = self.config.get("output_dir", "")
        self.inspector_name = self.config.get("inspector_name", "朱林初")

        # 将配置中的风险列表注入生成逻辑
        set_risk_lists(self.config.get("high_risk", []), self.config.get("low_risk", []))
        set_rate_ranges(self.config.get("rate_ranges", {}))
        self.history = []
        self.veg_placeholder = "例如: 白菜,菠菜,生菜"

        self.setup_ui()
        self.auto_set_today()

    def setup_ui(self):
        """
        设置用户界面布局。

        创建所有GUI组件，包括路径选择、日期输入、数据录入和控制按钮。
        """
        # 配置路径选择框架
        config_frame = ttk.LabelFrame(self.root, text=" 1. 路径锁定 (直接在选定目录下查找) ")
        config_frame.pack(fill="x", padx=20, pady=10)

        ttk.Button(config_frame, text="定位大表文件夹", command=self.set_big_path).grid(row=0, column=0,
                                                                                       padx=10, pady=5)
        self.label_big_path = ttk.Label(config_frame, text=self.path_big_root or "未设置", foreground="black" if self.path_big_root else "red")
        self.label_big_path.grid(row=0, column=1, sticky="w")

        ttk.Button(config_frame, text="定位小表文件夹", command=self.set_small_path).grid(row=1, column=0,
                                                                                         padx=10, pady=5)
        self.label_small_path = ttk.Label(config_frame, text=self.path_small_root or "未设置", foreground="black" if self.path_small_root else "red")
        self.label_small_path.grid(row=1, column=1, sticky="w")

        ttk.Button(config_frame, text="定位输出文件夹", command=self.set_output_path).grid(row=2, column=0,
                                                                                         padx=10, pady=5)
        self.label_output_path = ttk.Label(config_frame, text=self.path_output or "未设置", foreground="black" if self.path_output else "red")
        self.label_output_path.grid(row=2, column=1, sticky="w")

        # 检测日期框架
        date_frame = ttk.LabelFrame(self.root, text=" 2. 检测日期 ")
        date_frame.pack(fill="x", padx=20, pady=5)
        self.entry_inspector = ttk.Entry(date_frame, width=14)
        self.entry_inspector.insert(0, self.inspector_name)
        self.entry_inspector.pack(side="right", padx=5)
        ttk.Label(date_frame, text="核验员：").pack(side="right")
        self.combo_year = ttk.Combobox(date_frame, values=[2025, 2026, 2027], width=6, state="readonly")
        self.combo_year.set(2026)
        self.combo_month = ttk.Combobox(date_frame, values=[f"{i:02d}" for i in range(1, 13)], width=5, state="readonly")
        self.combo_day = ttk.Combobox(date_frame, values=[f"{i:02d}" for i in range(1, 32)], width=5, state="readonly")
        self.combo_year.pack(side="left", padx=5)
        ttk.Label(date_frame, text="年").pack(side="left")
        self.combo_month.pack(side="left", padx=5)
        ttk.Label(date_frame, text="月").pack(side="left")
        self.combo_day.pack(side="left", padx=5)
        ttk.Label(date_frame, text="日").pack(side="left")

        # 日期变更时校验合法性
        self.combo_year.bind("<<ComboboxSelected>>", self.validate_date)
        self.combo_month.bind("<<ComboboxSelected>>", self.validate_date)
        self.combo_day.bind("<<ComboboxSelected>>", self.validate_date)

        # 数据录入框架
        gen_frame = ttk.LabelFrame(self.root, text=" 3. 数据录入 ")
        gen_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 蔬菜输入子框架
        veg_subframe = tk.Frame(gen_frame)
        veg_subframe.pack(fill="x", padx=10, pady=5)
        ttk.Label(veg_subframe, text="蔬菜品种 (用逗号分隔或每行一个)").pack(anchor="w")
        self.vegetable_input = tk.Text(veg_subframe, font=('微软雅黑', 10), height=3, wrap=tk.WORD)
        self.vegetable_input.pack(fill="x", pady=2)
        self.vegetable_input.insert("1.0", self.veg_placeholder)  # 占位符
        self.vegetable_input.bind("<FocusIn>", lambda e: self.clear_placeholder(e, self.veg_placeholder))
        self.vegetable_input.bind("<FocusOut>", lambda e: self.restore_placeholder(e, self.veg_placeholder))
        self.vegetable_input.bind("<KeyRelease>", self.validate_veg_input)  # 实时验证
        self.vegetable_status = ttk.Label(veg_subframe, text="", foreground="gray")
        self.vegetable_status.pack(anchor="w")

        # 按钮栏
        btn_bar = tk.Frame(gen_frame)
        btn_bar.pack(fill="x", padx=10, pady=2)
        ttk.Button(btn_bar, text="🪄 自动生成抑制率", command=self.generate_rates).pack(side="left")
        ttk.Button(btn_bar, text="🔍 查重并删除重复", command=self.check_duplicates).pack(side="left", padx=10)
        ttk.Button(btn_bar, text="🗑️ 清除输入", command=self.clear_inputs).pack(side="left", padx=10)
        ttk.Button(btn_bar, text="📁 导入文件", command=self.import_from_file).pack(side="left", padx=10)
        self.label_count = ttk.Label(btn_bar, text="品种总数：0", foreground="#E91E63")
        self.label_count.pack(side="right")

        # JSON输入子框架
        json_subframe = tk.Frame(gen_frame)
        json_subframe.pack(fill="both", expand=True, padx=10, pady=5)
        ttk.Label(json_subframe, text="JSON 数据 (自动生成或手动编辑)").pack(anchor="w")
        self.json_text = scrolledtext.ScrolledText(json_subframe, height=12, font=('Consolas', 10), wrap=tk.WORD)
        self.json_text.pack(fill="both", expand=True)
        self.json_text.bind("<KeyRelease>", self.validate_json_input)  # 实时JSON验证
        self.json_status = ttk.Label(json_subframe, text="", foreground="gray")
        self.json_status.pack(anchor="w")

        ttk.Button(json_subframe, text="✨ 自动格式化 JSON", command=self.format_json).pack(anchor="e", pady=4)

        # 控制按钮框架
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=10)
        ttk.Button(ctrl_frame, text="🔄 重置数据", command=self.reset_form).grid(row=0, column=0, padx=10)
        ttk.Button(ctrl_frame, text="⚙️ 配置", command=self.open_config_window).grid(row=0, column=1, padx=10)
        ttk.Button(ctrl_frame, text="🚀 开启任务 (完美排版保护)", command=self.run_task).grid(row=0, column=2, padx=10)

        self.label_history = ttk.Label(self.root, text="等待操作...", foreground="#666")
        self.label_history.pack(pady=5)

    # 新增方法：清除占位符
    def clear_placeholder(self, event, placeholder):
        if self.vegetable_input.get("1.0", tk.END).strip() == placeholder:
            self.vegetable_input.delete("1.0", tk.END)
            self.vegetable_input.config(fg="black")

    def restore_placeholder(self, event, placeholder):
        if not self.vegetable_input.get("1.0", tk.END).strip():
            self.vegetable_input.insert("1.0", placeholder)
            self.vegetable_input.config(fg="gray")

    # 新增方法：实时验证蔬菜输入
    def validate_veg_input(self, event=None):
        raw = self.vegetable_input.get("1.0", tk.END).strip()
        if not raw or raw == self.veg_placeholder:
            self.vegetable_status.config(text="", foreground="gray")
            return
        try:
            vegs = parse_vegetable_list(raw)
            self.vegetable_status.config(text=f"✅ 有效 ({len(vegs)} 个品种)", foreground="green")
        except ValueError as e:
            self.vegetable_status.config(text=f"❌ {str(e)}", foreground="red")

    # 新增方法：实时验证JSON输入
    def validate_json_input(self, event=None):
        raw = self.json_text.get("1.0", tk.END).strip()
        if not raw:
            self.json_status.config(text="", foreground="gray")
            return
        try:
            data = parse_json_data(raw)
            self.json_status.config(text=f"✅ 有效 ({len(data)} 条记录)", foreground="green")
            self.label_count.config(text=f"品种总数：{len(data)}")
        except (ValueError, json.JSONDecodeError) as e:
            self.json_status.config(text=f"❌ {str(e)}", foreground="red")

    # 新增方法：清除输入
    def clear_inputs(self):
        self.vegetable_input.delete("1.0", tk.END)
        self.vegetable_input.insert("1.0", self.veg_placeholder)
        self.vegetable_input.config(fg="gray")
        self.json_text.delete("1.0", tk.END)
        self.label_count.config(text="品种总数：0")
        self.vegetable_status.config(text="", foreground="gray")
        self.json_status.config(text="", foreground="gray")
        logging.info("输入已清除")

    # 新增方法：从文件导入
    def import_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                self.vegetable_input.delete("1.0", tk.END)
                self.vegetable_input.insert("1.0", content)
                self.vegetable_input.config(fg="black")
                self.validate_veg_input()
                logging.info(f"从文件导入: {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败：{e}")
                logging.error(f"导入失败: {e}")

    def run_task(self):
        # 日期校验
        if not self.is_date_valid():
            messagebox.showwarning("日期无效", "请选择有效日期后再执行任务。")
            logging.error("日期无效")
            return

        # 路径有效性检查
        if not self.path_big_root or not self.path_small_root or not self.path_output:
            messagebox.showerror("缺失", "请先设置大表、小表和输出文件夹路径。")
            logging.error("路径未设置：大表、小表或输出目录为空")
            return

        if not os.path.isdir(self.path_big_root) or not os.path.isdir(self.path_small_root):
            messagebox.showerror("缺失", "大表或小表路径无效，请重新选择。")
            logging.error("路径无效：大表或小表路径不是文件夹")
            return

        if not os.path.isdir(self.path_output):
            messagebox.showerror("缺失", "输出路径无效，请重新选择。")
            logging.error("路径无效：输出路径不是文件夹")
            return

        big, small = self.get_target_files()
        if not os.path.exists(big) or not os.path.exists(small):
            logging.error(f"文件不存在: 大表={big}, 小表={small}")
            messagebox.showerror("缺失", f"文件不存在，请检查路径和日期是否匹配！\n\n大表: {big}\n小表: {small}")
            return

        logging.info(f"开始任务: 大表={os.path.basename(big)}, 小表={os.path.basename(small)}")
        try:
            raw_json = self.json_text.get("1.0", tk.END)
            data = parse_json_data(raw_json)
            if not data:
                messagebox.showerror("错误", "JSON 数据为空，请先生成或粘贴数据。")
                logging.error("JSON 数据为空")
                return

            date_label = self.config.get(
                "date_format", "{y}年{m}月{d}日"
            ).format(
                y=self.combo_year.get(),
                m=int(self.combo_month.get()),
                d=int(self.combo_day.get()),
            )
            inspector_name = self.entry_inspector.get().strip() or self.inspector_name

            # 处理文档（大表/小表）
            process_documents(big, small, data, date_label, self.path_output, inspector_name)

            self.update_history(f"成功导出: {os.path.basename(big)}")
            logging.info(f"任务成功完成: 导出 {os.path.basename(big)}")
            messagebox.showinfo("成功", "任务完成！日期和主检人已修改，排版 100% 完好无损！")

            # 保存核验员为上次使用值
            if inspector_name != self.config.get("inspector_name"):
                self.config["inspector_name"] = inspector_name
                save_config(self.config)
                logging.info(f"更新核验员: {inspector_name}")
        except FileNotFoundError as e:
            logging.error(f"文件不存在错误: {e}")
            messagebox.showerror("错误", f"文件不存在：{e}")
        except ValueError as e:
            logging.error(f"数据格式错误: {e}")
            messagebox.showerror("错误", str(e))
        except json.JSONDecodeError:
            logging.error("JSON 格式无效")
            messagebox.showerror("错误", "JSON 格式无效，请检查数据。")
        except PermissionError as e:
            logging.error(f"权限错误: {e}", exc_info=True)
            messagebox.showerror("错误", "输出文件被占用或没有权限，请关闭已打开的文档后重试。")
        except Exception as e:
            logging.error(f"未知错误: {e}", exc_info=True)
            messagebox.showerror("错误", f"发生未知错误：{e}")

    def get_target_files(self):
        y, m, d = self.combo_year.get(), self.combo_month.get(), self.combo_day.get()
        d_int = int(d)
        big = os.path.join(self.path_big_root, f"农残检测记录表{y}.{m}.{d}.docx")
        small = os.path.join(self.path_small_root, f"单位农残记录表{m}.{d_int}.docx")
        return big, small

    def auto_set_today(self):
        t = datetime.now()
        self.combo_year.set(t.year)
        self.combo_month.set(f"{t.month:02d}")
        self.combo_day.set(f"{t.day:02d}")

    def is_date_valid(self) -> bool:
        try:
            y = int(self.combo_year.get())
            m = int(self.combo_month.get())
            d = int(self.combo_day.get())
            datetime(y, m, d)
            return True
        except Exception:
            return False

    def validate_date(self, event=None):
        if self.is_date_valid():
            self.label_history.config(text="日期有效", foreground="#2E7D32")
        else:
            self.label_history.config(text="日期无效，请重新选择", foreground="#C62828")

    def generate_rates(self):
        try:
            if not self.is_date_valid():
                messagebox.showwarning("日期无效", "请选择有效日期后再生成抑制率。")
                return
            raw = self.vegetable_input.get("1.0", tk.END).strip()
            if not raw or raw == self.veg_placeholder:
                messagebox.showwarning("输入有误", "请输入蔬菜品种后再生成抑制率。")
                return
            vegs = parse_vegetable_list(raw)

            res = gen_inhibition_rates(vegs)
            self.json_text.delete("1.0", tk.END)
            self.json_text.insert(tk.END, format_json_data(res))
            self.label_count.config(text=f"品种总数：{len(res)}")
            logging.info(f"生成抑制率成功: {len(res)} 个品种")
        except ValueError as e:
            logging.warning(f"生成抑制率输入有误: {e}")
            messagebox.showwarning("输入有误", str(e))
        except Exception as e:
            logging.error(f"生成抑制率失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"生成抑制率失败：{e}")

    def format_json(self):
        try:
            data = parse_json_data(self.json_text.get("1.0", tk.END))
            self.json_text.delete("1.0", tk.END)
            self.json_text.insert(tk.END, format_json_data(data))
            self.label_count.config(text=f"品种总数：{len(data)}")
            self.json_status.config(text=f"✅ 已格式化 ({len(data)} 条记录)", foreground="green")
        except ValueError as e:
            messagebox.showwarning("输入有误", str(e))
        except json.JSONDecodeError:
            messagebox.showerror("错误", "JSON格式无效，请检查数据。")

    def check_duplicates(self):
        try:
            data = parse_json_data(self.json_text.get("1.0", tk.END))
            unique_data, removed = remove_duplicate_varieties(data)
            self.json_text.delete("1.0", tk.END)
            self.json_text.insert(tk.END, format_json_data(unique_data))
            self.label_count.config(text=f"品种总数：{len(unique_data)}")
            logging.info(f"查重完成: 删除了 {removed} 个重复品种")
            messagebox.showinfo("查重完成", f"删除了 {removed} 个重复品种。")
        except ValueError as e:
            logging.warning(f"查重输入有误: {e}")
            messagebox.showwarning("输入有误", str(e))
        except json.JSONDecodeError:
            logging.error("查重时 JSON 格式无效")
            messagebox.showerror("错误", "JSON格式无效，请检查数据。")
        except Exception as e:
            logging.error(f"查重失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"查重失败：{e}")

    def set_big_path(self):
        p = filedialog.askdirectory()
        if p:
            self.path_big_root = p
            self.label_big_path.config(text=p, foreground="black")
            self.config["big_path"] = p
            save_config(self.config)
            logging.info(f"大表路径设置为: {p}")

    def set_small_path(self):
        p = filedialog.askdirectory()
        if p:
            self.path_small_root = p
            self.label_small_path.config(text=p, foreground="black")
            self.config["small_path"] = p
            save_config(self.config)
            logging.info(f"小表路径设置为: {p}")

    def set_output_path(self):
        p = filedialog.askdirectory()
        if p:
            self.path_output = p
            self.label_output_path.config(text=p, foreground="black")
            self.config["output_dir"] = p
            save_config(self.config)
            logging.info(f"输出路径设置为: {p}")

    def open_config_window(self):
        """打开配置窗口，允许用户编辑配置项。"""
        config_win = tk.Toplevel(self.root)
        config_win.title("配置设置")
        config_win.geometry("600x500")

        # 输出目录
        tk.Label(config_win, text="输出目录:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.cfg_output_dir = tk.Entry(config_win, width=50)
        self.cfg_output_dir.insert(0, self.config.get("output_dir", ""))
        self.cfg_output_dir.grid(row=0, column=1, padx=10, pady=5)
        tk.Button(config_win, text="选择", command=lambda: self.select_output_dir(config_win)).grid(row=0, column=2)

        # 核验员姓名
        tk.Label(config_win, text="核验员姓名:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.cfg_inspector = tk.Entry(config_win, width=50)
        self.cfg_inspector.insert(0, self.config.get("inspector_name", ""))
        self.cfg_inspector.grid(row=1, column=1, padx=10, pady=5)

        # 日期格式
        tk.Label(config_win, text="日期格式:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.cfg_date_format = tk.Entry(config_win, width=50)
        self.cfg_date_format.insert(0, self.config.get("date_format", ""))
        self.cfg_date_format.grid(row=2, column=1, padx=10, pady=5)

        # 高风险蔬菜
        tk.Label(config_win, text="高风险蔬菜 (逗号分隔):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.cfg_high_risk = tk.Entry(config_win, width=50)
        self.cfg_high_risk.insert(0, ",".join(self.config.get("high_risk", [])))
        self.cfg_high_risk.grid(row=3, column=1, padx=10, pady=5)

        # 低风险蔬菜
        tk.Label(config_win, text="低风险蔬菜 (逗号分隔):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.cfg_low_risk = tk.Entry(config_win, width=50)
        self.cfg_low_risk.insert(0, ",".join(self.config.get("low_risk", [])))
        self.cfg_low_risk.grid(row=4, column=1, padx=10, pady=5)

        # 保存按钮
        tk.Button(config_win, text="保存配置", bg="#4CAF50", fg="white", command=lambda: self.save_config_from_window(config_win)).grid(row=5, column=0, columnspan=3, pady=20)

    def select_output_dir(self, parent_win):
        """选择输出目录。"""
        p = filedialog.askdirectory()
        if p:
            self.cfg_output_dir.delete(0, tk.END)
            self.cfg_output_dir.insert(0, p)

    def save_config_from_window(self, config_win):
        """从配置窗口保存配置。"""
        try:
            new_config = {
                "output_dir": self.cfg_output_dir.get().strip(),
                "inspector_name": self.cfg_inspector.get().strip(),
                "date_format": self.cfg_date_format.get().strip(),
                "high_risk": [v.strip() for v in self.cfg_high_risk.get().split(",") if v.strip()],
                "low_risk": [v.strip() for v in self.cfg_low_risk.get().split(",") if v.strip()],
            }
            # 保留原配置中的其他字段（如 big_path、small_path、rate_ranges）
            merged_config = dict(self.config)
            merged_config.update(new_config)

            save_config(merged_config)
            self.config = merged_config
            # 更新风险列表
            set_risk_lists(merged_config.get("high_risk", []), merged_config.get("low_risk", []))
            # 更新界面
            self.path_output = merged_config.get("output_dir")
            self.label_output_path.config(text=self.path_output, foreground="black")
            self.inspector_name = merged_config.get("inspector_name", "朱林初")
            self.entry_inspector.delete(0, tk.END)
            self.entry_inspector.insert(0, self.inspector_name)
            logging.info("配置保存成功")
            messagebox.showinfo("成功", "配置已保存！")
            config_win.destroy()
        except Exception as e:
            logging.error(f"配置保存失败: {e}", exc_info=True)
            messagebox.showerror("错误", f"保存配置失败: {e}")
    def update_history(self, msg):
        self.history.insert(0, f"[{datetime.now().strftime('%H:%M')}] {msg}")
        self.label_history.config(text="\n".join(self.history[:3]), foreground="blue")

    def reset_form(self):
        self.vegetable_input.delete("1.0", tk.END)
        self.vegetable_input.insert("1.0", self.veg_placeholder)
        self.vegetable_input.config(fg="gray")
        self.json_text.delete("1.0", tk.END)
        self.label_count.config(text="品种总数：0")
        self.vegetable_status.config(text="", foreground="gray")
        self.json_status.config(text="", foreground="gray")
        self.history.clear()
        self.label_history.config(text="等待操作...", foreground="#666")
        self.auto_set_today()


if __name__ == "__main__":
    import material_app

    material_app.main()
