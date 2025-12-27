import struct
import binascii
import os

def magic_fix_firmware():
    input_file = '623.8.1.bin'
    output_file = 'magic_623.bin'
    
    # --- 你的信息 ---
    MY_KEY = "3755393038123f07"
    MY_MAC = "00:11:32:A1:B2:C3"

    # --- 关键地址定义 ---
    ENV_START = 0xD0000
    DTB_TARGET = 0xD1000
    KERNEL_START = 0xD5000
    ENV_END = 0xE0000  # U-Boot 默认环境变量结束位置 (64KB)
    
    # 原始 DTB 位置
    DTB_SOURCE = 0xB0750
    DTB_SIZE = 6914

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print("正在构建‘特洛伊木马’环境变量包...")

    # 1. 搬运 DTB 到 0xD1000
    dtb_data = data[DTB_SOURCE : DTB_SOURCE + DTB_SIZE]
    if dtb_data[0:4] != b'\xd0\x0d\xfe\xed':
        print("Warning: DTB Magic check failed, but proceeding...")
    
    # 清空 D1000-D5000 区域并写入 DTB
    data[DTB_TARGET : KERNEL_START] = b'\x00' * (KERNEL_START - DTB_TARGET)
    data[DTB_TARGET : DTB_TARGET + DTB_SIZE] = dtb_data
    print(f"DTB 已就位: {hex(DTB_TARGET)}")

    # 2. 构造环境变量 (放在 D0000 开头)
    env_dict = {
        b'key': MY_KEY.encode('ascii'),
        b'ethaddr': MY_MAC.encode('ascii'),
        b'netdev': b'eth0',
        b'boot_targets': b'sata usb mmc0',
        b'image_name': b'Image',
        b'initrd_image': b'uInitrd',
        # 启动命令 (含 lzmadec)
        b'bootcmd': b'run syno_bootargs; sf probe; sf read 0x1000000 0x0D5000 0x306000; lzmadec 0x1000000 0x2000000; sf read 0x3000000 0x3DB000 0x410000; sf read 0x1000000 0xD1000 0x4000; i2c mw 0x45 0x33 0x72; i2c mw 0x45 0x3d 0x66; i2c mw 0x45 0x3e 0x66; i2c mw 0x45 0x34 0x00; i2c mw 0x45 0x36 0xff; booti 0x2000000 0x3000000 0x1000000',
        # 群晖参数
        b'syno_bootargs': b'setenv bootargs console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
    }

    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0' # 双 Null 结束符，告诉 U-Boot 变量到此为止

    # 写入环境变量到头部 (保留 CRC 占位符)
    payload_len = len(env_payload)
    if payload_len > (DTB_TARGET - ENV_START - 4):
        print("Error: Env vars too big!")
        return
    
    # 填入数据
    data[ENV_START + 4 : ENV_START + 4 + payload_len] = env_payload
    
    # 填充 0x00 直到 DTB 开始 (清理旧数据)
    data[ENV_START + 4 + payload_len : DTB_TARGET] = b'\x00' * (DTB_TARGET - (ENV_START + 4 + payload_len))

    # 3. 计算“全局” CRC (覆盖 D0000 到 E0000，包含内核!)
    # 这是骗过 U-Boot 的核心：把内核当做环境变量的一部分来计算校验和
    full_env_block = data[ENV_START + 4 : ENV_END]
    print(f"正在计算 64KB 区块 CRC (包含内核数据)...")
    crc = binascii.crc32(full_env_block) & 0xFFFFFFFF
    
    # 4. 写入 CRC 头
    data[ENV_START : ENV_START + 4] = struct.pack('<I', crc)

    with open(output_file, 'wb') as f:
        f.write(data)
    
    print(f"生成完毕: {output_file}")
    print(f"CRC32: {hex(crc)} (已包含内核指纹)")
    print("注意：刷入后千万不要执行 'saveenv'，否则会擦除内核！")

if __name__ == "__main__":
    magic_fix_firmware()
