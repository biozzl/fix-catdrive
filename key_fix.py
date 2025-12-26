import struct
import binascii
import os

def safe_unlock_firmware():
    input_file = '623.8.1.bin'
    output_file = 'unlocked_623_safe.bin'
    
    # 你的机器码
    MY_KEY = "3755393038123f07"
    # 你的MAC地址
    MY_MAC = "00:11:32:A1:B2:C3"

    ENV_OFFSET = 0xD0000
    # 【关键修正】环境变量最大不能超过 0x5000，我们用 0x4000 (16KB) 最安全
    ENV_SIZE = 0x4000 

    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    # --- 1. 验证内核区是否安全 ---
    # 检查 0xD5000 处是否有 LZMA 头部 (5D 00 ...)
    kernel_header = data[0xD5000:0xD5002]
    if kernel_header != b'\x5d\x00':
        print("警告：原始文件的内核头部似乎不标准，但我们依然会小心操作。")
    else:
        print("验证通过：原始内核数据完好。")

    # --- 2. 构造 623.8.1 完美环境变量 ---
    # 提取自原厂固件 0xA2A33 处的默认值
    env_dict = {
        b'key': MY_KEY.encode('ascii'),
        b'ethaddr': MY_MAC.encode('ascii'),
        b'netdev': b'eth0',
        b'boot_targets': b'sata usb mmc0',
        b'image_name': b'Image',
        b'initrd_image': b'uInitrd',
        
        # 核心启动逻辑 (lzmadec 解压是必须的)
        b'bootcmd': b'run syno_bootargs; sf probe; sf read 0x1000000 0x0D5000 0x306000; lzmadec 0x1000000 0x2000000; sf read 0x3000000 0x3DB000 0x410000; sf read 0x1000000 0xD1000 0x4000; i2c mw 0x45 0x33 0x72; i2c mw 0x45 0x3d 0x66; i2c mw 0x45 0x3e 0x66; i2c mw 0x45 0x34 0x00; i2c mw 0x45 0x36 0xff; booti 0x2000000 0x3000000 0x1000000',
        
        # 群晖专用参数
        b'syno_bootargs': b'setenv bootargs console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
    }

    # 构建数据块
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0' 

    # 检查是否溢出
    if len(env_payload) > (ENV_SIZE - 4):
        print(f"Error: 环境变量太大 ({len(env_payload)} > {ENV_SIZE-4})！")
        return

    # 填充至 16KB (0x4000)
    env_block = env_payload.ljust(ENV_SIZE - 4, b'\x00')

    # 计算 CRC32
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    final_env = struct.pack('<I', crc) + env_block

    # --- 3. 写入固件 ---
    # 只覆盖 0xD0000 - 0xD4000，绝对不碰 0xD5000
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = final_env

    # 再次检查 0xD5000 是否被篡改
    if data[0xD5000:0xD5002] != b'\x5d\x00' and kernel_header == b'\x5d\x00':
        print("严重错误：生成过程中内核数据被破坏！")
        return

    with open(output_file, 'wb') as f:
        f.write(data)
    
    print(f"安全修复完成！请刷入: {output_file}")
    print(f"写入 Key: {MY_KEY}")
    print(f"文件大小: {len(data)} (应为 8388608)")

if __name__ == "__main__":
    safe_unlock_firmware()
