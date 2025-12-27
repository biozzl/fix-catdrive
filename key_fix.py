import struct
import binascii
import os

def final_fix_firmware():
    input_file = '623.8.1.bin'
    output_file = 'final_fixed_623.bin'
    
    # 你的机器码
    MY_KEY = "3755393038123f07"
    MY_MAC = "00:11:32:A1:B2:C3"

    # 地址定义
    ENV_OFFSET = 0xD0000
    DTB_TARGET_OFFSET = 0xD1000
    KERNEL_OFFSET = 0xD5000
    
    # 原始固件中 DTB 的隐藏位置 (通过 Python 扫描发现)
    DTB_SOURCE_OFFSET = 0xB0750 
    DTB_SIZE = 6914 # 真实大小

    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    # --- 1. 搬运设备树 (DTB) ---
    print(f"正在从 {hex(DTB_SOURCE_OFFSET)} 提取 DTB...")
    dtb_data = data[DTB_SOURCE_OFFSET : DTB_SOURCE_OFFSET + DTB_SIZE]
    
    # 验证 DTB Magic (D0 0D FE ED)
    if dtb_data[0:4] != b'\xd0\x0d\xfe\xed':
        print("严重警告：源地址没有找到 DTB Magic！脚本可能需要调整。")
    else:
        print("DTB 验证通过，准备搬运。")

    # 写入到目标位置 0xD1000
    # 注意：先清空该区域 (0xD1000 - 0xD5000)
    data[DTB_TARGET_OFFSET : KERNEL_OFFSET] = b'\x00' * (KERNEL_OFFSET - DTB_TARGET_OFFSET)
    data[DTB_TARGET_OFFSET : DTB_TARGET_OFFSET + DTB_SIZE] = dtb_data
    print(f"DTB 已成功搬运到 {hex(DTB_TARGET_OFFSET)}")

    # --- 2. 注入 Key 和环境变量 ---
    # 注意：环境变量空间只能用 0xD0000 - 0xD1000 (4KB)，否则会覆盖刚搬过去的 DTB
    ENV_SIZE = 0x1000 
    
    env_dict = {
        b'key': MY_KEY.encode('ascii'),
        b'ethaddr': MY_MAC.encode('ascii'),
        b'netdev': b'eth0',
        b'boot_targets': b'sata usb mmc0',
        b'image_name': b'Image',
        b'initrd_image': b'uInitrd',
        
        # 623 启动命令
        b'bootcmd': b'run syno_bootargs; sf probe; sf read 0x1000000 0x0D5000 0x306000; lzmadec 0x1000000 0x2000000; sf read 0x3000000 0x3DB000 0x410000; sf read 0x1000000 0xD1000 0x4000; i2c mw 0x45 0x33 0x72; i2c mw 0x45 0x3d 0x66; i2c mw 0x45 0x3e 0x66; i2c mw 0x45 0x34 0x00; i2c mw 0x45 0x36 0xff; booti 0x2000000 0x3000000 0x1000000',
        
        # 群晖参数
        b'syno_bootargs': b'setenv bootargs console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
    }

    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0' 

    if len(env_payload) > (ENV_SIZE - 4):
        print(f"Error: 环境变量太大 ({len(env_payload)})，超过 4KB 限制！")
        return

    env_block = env_payload.ljust(ENV_SIZE - 4, b'\x00')
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    final_env = struct.pack('<I', crc) + env_block

    # 写入环境变量 (0xD0000)
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = final_env

    # --- 3. 保存 ---
    with open(output_file, 'wb') as f:
        f.write(data)
    
    print(f"完美固件生成完毕: {output_file}")
    print("包含了 Key、修复了 DTB 位置、保留了内核。请刷入！")

if __name__ == "__main__":
    final_fix_firmware()
