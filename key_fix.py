import struct
import binascii
import os

def create_unlocked_firmware():
    input_file = '623.8.1.bin'
    output_file = 'unlocked_623.bin'
    
    # 你的机器码
    MY_KEY = "3755393038123f07"
    # 你的MAC地址 (沿用之前oldbin的，或者你自行修改)
    MY_MAC = "00:11:32:A3:67:EF"

    ENV_OFFSET = 0xD0000
    ENV_SIZE = 0x10000 # 64KB

    if not os.path.exists(input_file):
        print(f"找不到 {input_file}")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    # --- 构造 623.8.1 专属环境变量 ---
    # 这些参数是我直接从二进制文件 0xA2A33 处提取的原厂默认值
    env_dict = {
        b'key': MY_KEY.encode('ascii'),
        b'ethaddr': MY_MAC.encode('ascii'),
        
        # 核心启动参数 (提取自固件)
        b'syno_bootargs': b'setenv bootargs console=ttyS0,115200 ip=off initrd=0x3000000 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_castrated_xhc=d0058000.usb3@1 swiotlb=2048 syno_hw_version=DS120j syno_fw_version=M.301 syno_hdd_powerup_seq=1 ihd_num=1 netif_num=1 syno_hdd_enable=40 syno_hdd_act_led=10 flash_size=8',
        
        # 核心引导命令 (提取自固件，包含 LZMA 解压)
        b'bootcmd': b'run syno_bootargs; sf probe; sf read 0x1000000 0x0D5000 0x306000; lzmadec 0x1000000 0x2000000; sf read 0x3000000 0x3DB000 0x410000; sf read 0x1000000 0xD1000 0x4000; i2c mw 0x45 0x33 0x72; i2c mw 0x45 0x3d 0x66; i2c mw 0x45 0x3e 0x66; i2c mw 0x45 0x34 0x00; i2c mw 0x45 0x36 0xff; booti 0x2000000 0x3000000 0x1000000',
        
        # 其他必要变量
        b'image_name': b'Image',
        b'netdev': b'eth0',
        b'boot_targets': b'sata usb mmc0',
    }

    # 构建数据块
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0' # 结束符

    # 填充至 64KB - 4字节
    env_block = env_payload.ljust(ENV_SIZE - 4, b'\x00')

    # 计算 CRC32
    crc = binascii.crc32(env_block) & 0xFFFFFFFF
    final_env = struct.pack('<I', crc) + env_block

    # 写入固件
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = final_env

    with open(output_file, 'wb') as f:
        f.write(data)
    
    print(f"成功！已生成解锁版固件: {output_file}")
    print(f"Key 已注入: {MY_KEY}")
    print(f"CRC32: {hex(crc)}")

if __name__ == "__main__":
    create_unlocked_firmware()
