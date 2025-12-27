import struct
import binascii
import os

def create_custom_firmware():
    # 源文件 (必须是那个干净的 ultimate 版本)
    input_file = 'hybrid_ultimate.bin'
    # 输出文件 (保持原名，方便你不用改 Action 配置)
    output_file = 'hybrid_custom_mac_sn.bin'
    
    # --- 你的定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}！请确保它在仓库根目录。")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在生成完美校验版固件...")
    print(f"  MAC: {NEW_MAC_STR}")
    print(f"  SN : {NEW_SN_STR}")

    # ==============================
    # 1. 修改 Vendor 分区 (物理层)
    # ==============================
    vendor_offset = 0x7EB000
    
    # 1.1 写入 MAC 地址 (6字节)
    mac_hex = NEW_MAC_STR.replace(':', '')
    mac_bytes = bytes.fromhex(mac_hex)
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    
    # 1.2 [关键新增] 计算并写入 MAC 校验位
    # 规则：MAC 6字节求和，取最后 1 字节 (LSB)
    # 例如: Sum = 572 (0x23C) -> Checksum = 0x3C
    mac_sum = sum(mac_bytes)
    mac_checksum = mac_sum & 0xFF
    
    # 写入到 MAC 后的第 7 个字节
    data[vendor_offset + 6] = mac_checksum
    
    print(f"  [Vendor] MAC 写入成功")
    print(f"  [Vendor] MAC 校验值计算: Sum={mac_sum} (0x{mac_sum:X}) -> Byte=0x{mac_checksum:02X}")

    # 1.3 计算 SN 的校验和 (CHK)
    # 规则：SN 字符串 ASCII 累加
    chk_sum = 0
    for char in NEW_SN_STR:
        chk_sum += ord(char)
    
    # 1.4 写入 SN 字符串
    # 格式: SN=xxxxxxxx,CHK=xxx
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    vendor_bytes = vendor_str.encode('ascii')
    
    # 为了防止覆盖 MAC，我们将 SN 字符串写在 MAC 后面一段距离
    # 0x7EB000 + 0x20 (32字节后) 是一个很安全的位置
    target_idx = vendor_offset + 0x20
    
    # 写入前先清空这一小块区域 (防止旧数据残留)
    data[target_idx : target_idx + 128] = b'\x00' * 128
    # 写入新数据
    data[target_idx : target_idx + len(vendor_bytes)] = vendor_bytes
    
    print(f"  [Vendor] SN 写入成功: {vendor_str} (CHK={chk_sum})")

    # ==============================
    # 2. 修改 U-Boot 环境变量 (软件层)
    # ==============================
    env_offset = 0xD0000
    env_size = 0x1000
    
    # 提取现有环境块
    env_block = data[env_offset + 4 : env_offset + env_size]
    env_items = env_block.split(b'\0')
    new_env_items = []
    
    # 替换 ethaddr
    mac_replaced = False
    for item in env_items:
        if not item: continue
        if item.startswith(b'ethaddr='):
            new_env_items.append(b'ethaddr=' + NEW_MAC_STR.encode('ascii'))
            mac_replaced = True
        else:
            new_env_items.append(item)
    
    if not mac_replaced:
        new_env_items.append(b'ethaddr=' + NEW_MAC_STR.encode('ascii'))
        
    # 重组并计算 CRC
    new_env_payload = b'\0'.join(new_env_items) + b'\0\0'
    new_env_block = new_env_payload.ljust(env_size - 4, b'\x00')
    new_crc = binascii.crc32(new_env_block) & 0xFFFFFFFF
    
    # 写入 CRC 和数据
    final_env = struct.pack('<I', new_crc) + new_env_block
    data[env_offset : env_offset + env_size] = final_env
    print(f"  [Env] U-Boot 环境变量更新完毕 (CRC: {hex(new_crc)})")

    # ==============================
    # 3. 保存文件
    # ==============================
    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！{output_file} 生成完毕。")
    print("该固件已包含 MAC 校验位修复。")

if __name__ == "__main__":
    create_custom_firmware()
