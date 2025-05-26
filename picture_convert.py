import os
import math # 用于计算数字长度

def rename_images_in_folder_interactive(folder_path, base_name="frame", sort_order="name"):
    """
    将指定文件夹中的图片文件按顺序重命名，并在执行前请求用户确认。

    参数:
    folder_path (str): 包含图片的文件夹路径。
    base_name (str): 新文件名的基本名称，例如 "frame"。
    sort_order (str): 排序方式，可选 "name" (文件名，默认) 或 "mtime" (修改时间)。
    """

    if not os.path.isdir(folder_path):
        print(f"错误：文件夹 '{folder_path}' 未找到或不是一个有效的目录。")
        return

    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.heif')
    files_in_folder = os.listdir(folder_path)
    
    image_files = []
    for f_name in files_in_folder:
        full_path = os.path.join(folder_path, f_name)
        if os.path.isfile(full_path) and f_name.lower().endswith(image_extensions):
            image_files.append(f_name)

    if not image_files:
        print(f"在文件夹 '{folder_path}' 中未找到支持的图片文件。")
        return

    if sort_order == "name":
        image_files.sort()
        print("图片将按文件名（字母顺序）排序后重命名。")
    elif sort_order == "mtime":
        try:
            image_files.sort(key=lambda f: os.path.getmtime(os.path.join(folder_path, f)))
            print("图片将按修改时间（从旧到新）排序后重命名。")
        except Exception as e:
            print(f"按修改时间排序失败，将使用默认文件名排序：{e}")
            image_files.sort()
    else:
        print(f"未知的排序方式 '{sort_order}'。将使用默认文件名排序。")
        image_files.sort()

    num_files = len(image_files)
    if num_files == 0:
        print("没有符合条件的图片文件可供重命名。")
        return
        
    padding_digits = len(str(num_files))
    
    rename_plan = [] # 用于存储计划的操作
    
    print(f"\n--- 计划重命名预览 (共 {num_files} 个符合条件的文件) ---")
    print(f"将基于 '{base_name}' 和 {padding_digits} 位序号进行重命名：")

    potential_actions_count = 0
    for index, old_filename in enumerate(image_files):
        original_base, original_extension = os.path.splitext(old_filename)
        original_extension = original_extension.lower()
        new_number_part = str(index + 1).zfill(padding_digits)
        new_filename = f"{base_name}{new_number_part}{original_extension}"

        old_path = os.path.join(folder_path, old_filename)
        new_path = os.path.join(folder_path, new_filename)
        
        action_item = {
            'old_filename': old_filename, 'new_filename': new_filename,
            'old_path': old_path, 'new_path': new_path,
            'status': '', 'message': ''
        }

        if old_path == new_path:
            action_item['status'] = 'skip_already_correct'
            action_item['message'] = f"  [跳过] '{old_filename}' -> 文件名已是目标格式。"
        elif os.path.exists(new_path):
            action_item['status'] = 'skip_target_exists'
            action_item['message'] = f"  [警告] '{old_filename}' -> '{new_filename}' (目标文件已存在，将跳过此操作)。"
        else:
            action_item['status'] = 'plan_rename'
            action_item['message'] = f"  [计划] '{old_filename}' -> '{new_filename}'"
            potential_actions_count += 1
        
        print(action_item['message'])
        rename_plan.append(action_item)

    if potential_actions_count == 0:
        print("\n没有需要执行的重命名操作。")
        # 打印总结，即使没有实际操作
        total_skipped = sum(1 for item in rename_plan if item['status'] != 'plan_rename')
        print("\n--- 操作总结 ---")
        print(f"计划重命名: 0 个文件。")
        print(f"跳过（已符合格式或目标已存在）: {total_skipped} 个文件。")
        print("无需用户确认，未做任何更改。")
        return

    print("--- 预览结束 ---")
    
    try:
        # Python 2/3兼容性考虑，但对于现代Python，直接input即可
        user_confirmation = input(f"\n是否要执行以上 {potential_actions_count} 个计划的重命名操作? (输入 'yes' 确认, 其他则取消): ").strip().lower()
    except EOFError: # 处理在某些环境下input可能引发EOFError的情况 (例如，如果stdin被重定向且为空)
        user_confirmation = "no"
        print("\n无法获取用户输入，默认取消操作。")


    if user_confirmation == 'yes':
        print("\n--- 正在执行重命名 ---")
        renamed_count = 0
        error_count = 0
        actually_skipped_during_execution = 0 # 记录执行阶段的跳过

        for item in rename_plan:
            if item['status'] == 'plan_rename':
                try:
                    # 再次检查目标是否存在，以防万一在计划和执行之间发生变化
                    # （对于单线程脚本，此风险较小，但良好实践）
                    if os.path.exists(item['new_path']):
                        print(f"  [执行时跳过] '{item['old_filename']}' -> '{item['new_filename']}' (目标文件在执行时发现已存在)。")
                        actually_skipped_during_execution += 1
                        continue

                    os.rename(item['old_path'], item['new_path'])
                    print(f"  [成功] '{item['old_filename']}' -> '{item['new_filename']}'")
                    renamed_count += 1
                except OSError as e:
                    print(f"  [错误] 重命名 '{item['old_filename']}' 到 '{item['new_filename']}' 失败: {e}")
                    error_count += 1
            # else: # 其他状态（如skip_already_correct, skip_target_exists）在计划阶段已处理，执行阶段不再重复打印

        print("\n--- 操作总结 ---")
        print(f"实际重命名: {renamed_count} 个文件。")
        # 重新计算总跳过数，包括计划阶段和执行阶段新发现的跳过
        total_skipped = sum(1 for item in rename_plan if item['status'] != 'plan_rename') + actually_skipped_during_execution
        print(f"跳过（已符合格式/目标已存在/执行时发现目标已存在）: {total_skipped} 个文件。")
        print(f"发生错误: {error_count} 个文件。")

    else:
        print("\n用户取消操作。没有文件被实际修改。")
        total_skipped = sum(1 for item in rename_plan if item['status'] != 'plan_rename')
        print("\n--- 操作总结 (未执行) ---")
        print(f"原计划重命名: {potential_actions_count} 个文件。")
        print(f"原计划跳过: {total_skipped} 个文件。")


# --- 如何使用 ---
if __name__ == "__main__":
    # 1. 指定包含原始图片的文件夹路径
    target_folder_path = r"G:\CodePet\ezgif-split (2)"  # <--- 修改这里为你的图片文件夹路径

    # 2. (可选) 新文件名的基础部分
    file_base_name = "frame"

    # 3. (可选) 排序方式："name" (按原文件名) 或 "mtime" (按修改时间)
    sort_method = "name"
    # sort_method = "mtime" # 如果想按修改时间排序，取消这行注释，并注释掉上一行

    # 检查示例文件夹是否存在
    if not os.path.isdir(target_folder_path) and target_folder_path == "your_image_folder_here":
        print(f"提示：请将脚本中的 'your_image_folder_here' 替换为实际的图片文件夹路径。")
        print(f"你可以手动创建一个文件夹并放入一些图片进行测试。")
    else:
        rename_images_in_folder_interactive(target_folder_path, file_base_name, sort_method)