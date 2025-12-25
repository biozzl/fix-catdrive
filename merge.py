import os

def merge_firmware():
    # 文件名配置
    file_uboot = "old.bin"   # 原厂无锁 U-Boot
    file_kernel = "new.bin"  # 猫盘专用 Kernel/DTB
    file_out = "mixed.bin"   # 输出结果

    # 分割点地址: 0xCC800
    # 0 ~ 0xCC800 是 U-Boot 和环境变量区域
    # 0xCC800 之后 是 DTB、Kernel 和 Ramdisk
    SPLIT_POINT = 0xCC800

    print(f"开始合并...")
    
    with open(file_uboot, "rb") as f_u, open(file_kernel, "rb") as f_k, open(file_out, "wb") as f_o:
        # 1. 读取 old.bin 的前半部分 (无锁 U-Boot)
        f_u.seek(0)
        uboot_data = f_u.read(SPLIT_POINT)
        f_o.write(uboot_data)
        print(f"已写入 U-Boot: {len(uboot_data)} 字节 (来自 {file_uboot})")

        # 2. 读取 new.bin 的后半部分 (猫盘驱动)
        f_k.seek(SPLIT_POINT)
        kernel_data = f_k.read() # 读取直到文件结束
        f_o.write(kernel_data)
        print(f"已写入 Kernel/DTB: {len(kernel_data)} 字节 (来自 {file_kernel})")

    print(f"完成! 生成文件: {file_out}")

if __name__ == "__main__":
    if os.path.exists("old.bin") and os.path.exists("new.bin"):
        merge_firmware()
    else:
        print("错误: 找不到 bin 文件")
