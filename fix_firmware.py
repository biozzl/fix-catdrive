import struct
import binascii
import os

def patch_bin(input_file, output_file):
    # 猫盘标准环境变量偏移与大小
    ENV_OFFSET = 0xD0000
    ENV_SIZE = 0x10000  # 64KB
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    # --- 补丁基因定义 ---
    # 这里根据你成功的日志，硬编码了所有修复逻辑
    env_dict = {
        b'bootargs': b'console=ttyS0,115200 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_hw_version=DS120j syno_hdd_enable=40 flash_size=8',
        b'bootcmd': b'sf probe; sf read 0x2000000 0xd5000 0x306000; sf read 0x3000000 0x3db000 0x410000; sf read 0x1000000 0xcc800 0x3000; bootm 0x2000000 0x3000000 0x1000000',
        b'preboot': b'i2c dev 0; i2c probe 46; if test $? = 0; then mw.l 0xd0032004 0x0; fi',
        b'ethaddr': b'00:11:32:A1:B2:C3' # 这里可以手动改成你贴纸上的MAC
    }

    # 构建环境变量块 (从第5字节开始)
    new_env_content = bytearray()
    for k, v in env_dict.items():
        new_env_content += k + b'=' + v + b'\0'
    new_env_content += b'\0' # 结尾双空字符

    # 填充 0x00 直到 64KB-4字节
    new_env_block_data = new_env_content.ljust(ENV_SIZE - 4, b'\x00')

    # 计算 CRC32 并写入前4字节 (小端序)
    crc = binascii.crc32(new_env_block_data) & 0xFFFFFFFF
    final_env_block = struct.pack('<I', crc) + new_env_block_data

    # 缝合到 D0000
    data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = final_env_block

    with open(output_file, 'wb') as f:
        f.write(data)
    
    print(f"Build Success: {output_file}")
    print(f"CRC32 Checksum: {hex(crc)}")

if __name__ == "__main__":
    patch_bin('old.bin', 'fixed_old.bin')
