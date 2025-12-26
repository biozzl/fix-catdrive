import struct
import binascii
import os

def final_fix():
    file_path = 'old.bin'
    output_path = 'fixed_old.bin'
    
    # 定义猫盘环境变量的标准参数
    ENV_OFFSET = 0xD0000
    ENV_SIZE = 0x10000  # 64KB
    
    if not os.path.exists(file_path):
        print(f"找不到 {file_path}")
        return

    # 读取原始数据
    with open(file_path, 'rb') as f:
        full_data = bytearray(f.read())
    
    if len(full_data) != 8388608:
        print(f"警告：原始文件大小不是8MB，当前为 {len(full_data)} 字节")

    # 1. 构建干净的环境变量字典
    # 只注入必要的补丁，不改变内核读取逻辑
    env_dict = {
        b'bootargs': b'console=ttyS0,115200 root=/dev/sda1 rw syno_usb_vbus_gpio=36@d0058000.usb3@1@0,37@d005e000.usb@1@0 syno_hw_version=DS120j syno_hdd_enable=40 flash_size=8',
        b'preboot': b'i2c dev 0; i2c probe 46; if test $? = 0; then mw.l 0xd0032004 0x0; fi',
        b'ethaddr': b'00:11:32:A1:B2:C3', # 请在此处填入你的真实MAC
    }

    # 2. 生成环境变量二进制块
    env_payload = bytearray()
    for k, v in env_dict.items():
        env_payload += k + b'=' + v + b'\0'
    env_payload += b'\0' # 结尾双空

    # 严格限制长度为 ENV_SIZE - 4 (CRC位)
    env_block_data = env_payload.ljust(ENV_SIZE - 4, b'\x00')

    # 3. 计算 CRC32
    crc = binascii.crc32(env_block_data) & 0xFFFFFFFF
    
    # 组合成最终的 64KB 块
    new_env_area = struct.pack('<I', crc) + env_block_data

    # 4. 精准缝合：原地替换，不改变前后数据位置
    full_data[ENV_OFFSET : ENV_OFFSET + ENV_SIZE] = new_env_area

    # 5. 输出
    with open(output_path, 'wb') as f:
        f.write(full_data)
    
    print("--- 修复报告 ---")
    print(f"1. 环境变量起始地址: {hex(ENV_OFFSET)}")
    print(f"2. 写入 CRC32 值: {hex(crc)}")
    print(f"3. 最终文件大小: {len(full_data)} (必须是8388608)")
    print("----------------")
    print("修复完成！请将 fixed_old.bin 刷入。")

if __name__ == "__main__":
    final_fix()
