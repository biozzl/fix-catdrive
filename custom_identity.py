import struct
import binascii
import os

def create_custom_firmware():
    input_file = 'hybrid_ultimate.bin'
    output_file = 'hybrid_custom_mac_sn.bin'
    
    # --- 你的定制信息 ---
    NEW_MAC_STR = "00:11:32:A3:67:EF"
    NEW_SN_STR  = "1910Q2N321313"
    
    if not os.path.exists(input_file):
        print(f"Error: 找不到 {input_file}，请先生成它！")
        return

    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    print(f"正在修改身份信息...")
    print(f"  目标 MAC: {NEW_MAC_STR}")
    print(f"  目标 SN : {NEW_SN_STR}")

    # ==============================
    # 1. 修改 Vendor 分区 (物理层)
    # ==============================
    vendor_offset = 0x7EB000
    
    # 1.1 修改二进制 MAC (前6字节)
    mac_bytes = bytes.fromhex(NEW_MAC_STR.replace(':', ''))
    data[vendor_offset : vendor_offset + 6] = mac_bytes
    print(f"  [Vendor] 物理 MAC 已写入")

    # 1.2 计算 SN 的校验和 (CHK)
    # 算法：将 SN 字符串中每个字符的 ASCII 值相加
    chk_sum = 0
    for char in NEW_SN_STR:
        chk_sum += ord(char)
    print(f"  [Vendor] 新 SN 校验和 (CHK): {chk_sum}")

    # 1.3 构造完整的 Vendor 字符串
    # 格式: SN=xxxxxxxxxxxxx,CHK=xxx
    vendor_str = f"SN={NEW_SN_STR},CHK={chk_sum}"
    vendor_bytes = vendor_str.encode('ascii')
    
    # 1.4 写入 Vendor 字符串
    # 寻找旧的 "SN=" 标记进行覆盖，或者直接写在 MAC 后面的固定位置
    # 原厂固件通常从 MAC 后的第 22 字节 (0x16) 或 32 字节 (0x20) 开始，或者直接搜索
    # 为了保险，我们搜索 "SN="
    vendor_chunk = data[vendor_offset : vendor_offset + 512]
    sn_idx = vendor_chunk.find(b'SN=')
    
    if sn_idx != -1:
        target_idx = vendor_offset + sn_idx
        # 清除旧的字符串 (填 0x00，直到遇到下一个 0x00 或一定长度)
        # 简单起见，我们直接覆盖，并在末尾补 0
        data[target_idx : target_idx + len(vendor_bytes)] = vendor_bytes
        data[target_idx + len(vendor_bytes)] = 0x00 # 结束符
        print(f"  [Vendor] SN 字符串已更新: {vendor_str}")
    else:
        print("  [Warning] 没找到旧的 SN 标记，尝试强制写入默认位置...")
        # 如果没找到，我们写在 MAC 后面一点的安全位置，比如 0x7EB040
        target_idx = vendor_offset + 0x40
        data[target_idx : target_idx + len(vendor_bytes)] = vendor_bytes
        data[target_idx + len(vendor_bytes)] = 0x00

    # ==============================
    # 2. 修改 U-Boot 环境变量 (软件层)
    # ==============================
    env_offset = 0xD0000
    env_size = 0x1000
    
    # 提取现有环境变量块 (跳过 CRC)
    env_block = data[env_offset + 4 : env_offset + env_size]
    
    # 解析并替换 ethaddr
    env_items = env_block.split(b'\0')
    new_env_items = []
    mac_replaced = False
    
    for item in env_items:
        if not item: continue # 跳过空
        if item.startswith(b'ethaddr='):
            new_env_items.append(b'ethaddr=' + NEW_MAC_STR.encode('ascii'))
            mac_replaced = True
        else:
            new_env_items.append(item)
    
    if not mac_replaced:
        new_env_items.append(b'ethaddr=' + NEW_MAC_STR.encode('ascii'))
        
    # 重组环境变量
    new_env_payload = b'\0'.join(new_env_items) + b'\0\0'
    
    # 填充并计算 CRC
    new_env_block = new_env_payload.ljust(env_size - 4, b'\x00')
    new_crc = binascii.crc32(new_env_block) & 0xFFFFFFFF
    
    # 写入
    final_env = struct.pack('<I', new_crc) + new_env_block
    data[env_offset : env_offset + env_size] = final_env
    print(f"  [Env] 环境变量 ethaddr 已更新 (CRC: {hex(new_crc)})")

    # ==============================
    # 3. 保存
    # ==============================
    with open(output_file, 'wb') as f:
        f.write(data)
        
    print(f"\n成功！定制版固件已生成: {output_file}")
    print("请刷入此文件，它包含了你指定的 MAC 和 SN。")

if __name__ == "__main__":
    create_custom_firmware()
