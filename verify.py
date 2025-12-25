import os

def check_firmware_health():
    print(">>> 开始对 mixed.bin 进行安全体检...\n")
    
    file_mixed = "mixed.bin"
    file_old = "old.bin" # 请确保这是您的原厂无锁固件

    # 1. 检查文件是否存在
    if not (os.path.exists(file_mixed) and os.path.exists(file_old)):
        print("❌ 错误: 找不到文件，请确保 mixed.bin 和 old.bin 都在当前目录下。")
        return

    # 2. 检查文件大小 (必须精确为 8MB)
    size = os.path.getsize(file_mixed)
    if size == 8388608:
        print(f"✅ [通过] 文件大小校验: {size} 字节 (8MB)，完美。")
    else:
        print(f"❌ [失败] 文件大小错误: {size} 字节。应该是 8388608 字节。")
        return

    # 3. 核心检查: U-Boot 区域 (0 - 0xCC800) 是否被篡改
    # 这是最重要的！如果这里变了，就会变砖。
    print(">>> 正在进行 U-Boot 基因比对...")
    with open(file_mixed, "rb") as fm, open(file_old, "rb") as fo:
        uboot_mixed = fm.read(0xCC800)
        uboot_old = fo.read(0xCC800)
        
        if uboot_mixed == uboot_old:
            print("✅ [通过] U-Boot 区域与原厂固件完全一致！(安全，不会刷死)")
        else:
            print("❌ [危险] U-Boot 区域被修改了！千万不要刷入！")
            return

        # 4. 检查是否成功植入了设备树 (Magic: D0 0D FE ED)
        # 我们把设备树搬到了 0xCC800
        fm.seek(0xCC800)
        dtb_magic = fm.read(4)
        if dtb_magic == b'\xd0\x0d\xfe\xed':
            print("✅ [通过] 设备树 (DTB) 已成功植入到 0xCC800。")
        else:
            print(f"❌ [失败] 0xCC800 处未发现设备树头，发现的是: {dtb_magic.hex()}")

        # 5. 检查是否成功植入了内核 (Magic: 27 05 19 56)
        # 应该在 0xD5000
        fm.seek(0xD5000)
        kernel_magic = fm.read(4)
        if kernel_magic == b'\x27\x05\x19\x56':
            print("✅ [通过] 内核 (Kernel) 已成功植入到 0xD5000。")
        else:
            print(f"❌ [失败] 0xD5000 处未发现内核头，发现的是: {kernel_magic.hex()}")

    print("\n🎉 结论: 固件健康，可以放心刷入！")

if __name__ == "__main__":
    check_firmware_health()
