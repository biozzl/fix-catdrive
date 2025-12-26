import struct
import binascii
import os

def generate_bubt_patch(input_file, output_file):
    # 只需要修改环境变量区，也就是 0xD0000 处
    ENV_OFFSET = 0xD0000
    ENV_SIZE = 0x10000
    
    with open(input_file, 'rb') as f:
        full_data = bytearray(f.read())

    # 1. 重新构建环境变量
    env_dict = {
        b'bootargs': b'console=ttyS0,115200 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_hw_version=DS120j syno_hdd_enable=40 flash_size=8',
        b'preboot': b'i2c dev 0; i2c probe 46; if test $? = 0; then mw.l 0xd0032004 0x0; fi',
        # 注意：这里我们不写死 bootcmd，让系统去跑它默认的逻辑，只改上面两个补丁
        b'ethaddr': b'00:11:32:A1:B2:C3',
    }

    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0'
    
    env_block_full = env_payload.ljust(ENV_SIZE - 4, b'\x00')
    crc = binascii.crc32(env_block_full) & 0xFFFFFFFF
    final_env_area = struct.pack('<I', crc) + env_block_full

    # 2. 注入回数据
    full_data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = final_env_area

    # 3. 关键：为了骗过 bubt，我们需要提取前 1MB 并确保它有一个 kwb 头部
    # 如果 bubt 依然报 Header 错误，说明它校验的是整块 SPI 映射
    # 我们直接导出这个 8MB 的文件，但在 U-Boot 里不用 bubt，用 sf 命令
    with open(output_file, 'wb') as f:
        f.write(full_data)
    
    print(f"Done. CRC: {hex(crc)}")

if __name__ == "__main__":
    generate_bubt_patch('old.bin', 'fixed_old.bin')
