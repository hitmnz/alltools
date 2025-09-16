import re

def parse_juniper_config(config_text):
    output = config_text

    interface_pattern = re.compile(r'((xe|ge|et)-([^\s.]+)(?::(\d+))?)') # group 1 # group 3 interface_number
    agregado_pattern = re.compile(r'(ae\S+)')
    unit_pattern = re.compile(r'unit (\d+\S)')
    description_pattern = re.compile (r'description "Cliente\[VPN]-(NNIL2|Direct)-([^-]*)-([^-]*)-([^-]*)-([^-]*)-(\((.*?)\))(\((.*?)\))(\@.*@)') ## Con distintos grupos para cada campo
    admin_number_pattern = re.compile (r'description "Cliente\[VPN]-(NNIL2|Direct)-([^-]*)-([^-]*)-([^-]*)-([^-]*)-(\((.*?)\))(\((.*?)\))(\@.*@)') ## group 9
    description_full_pattern = re.compile (r'"(Cliente.+)"')
    c_tag_pattern = re.compile (r'vlan-tags inner (\d+)') # group 2
    s_tag_pattern = re.compile (r'vlan-tags outer (\d+)') # group 1
    vlan_id_pattern = re.compile (r'vlan-id (\d+)') # group 1
    ipv4_address_pattern = re.compile (r'address (\d+\.\d+\.\d+\.\d+)')
    ipv6_address_pattern = re.compile (r'address (\w+\:\w+\:\w+\:\w+\:\w+\:\w+\:\w+\:\w+)') #group 1
    ipv6_mask_pattern = re.compile (r'address (\w+\:\w+\:\w+\:\w+\:\w+\:\w+\:\w+\:\w+(\/\d+))') #group 2
    mask_pattern = re.compile (r'address (\d+\.\d+\.\d+\.\d+)(\/\d+)') ## group 2
    mtu_pattern = re.compile (r'mtu (\d+)')
    vpn_name_pattern = re.compile (r'(vpn_([0-9]+)_([0-9]+))')
    internal_vpn_id_pattern = re.compile (r'route-distinguisher (\d+.\d+.\d+.+\d+)\:(\d+)') # group 2
    ip_loopback_pe_pattern = re.compile (r'route-distinguisher (\d+.\d+.\d+.+\d+)\:(\d+)') # group 1
    as_vpn_id_pattern = re.compile (r'(vpn_([0-9]+)_([0-9]+))') #group 2
    vpn_id_pattern = re.compile (r'(vpn_([0-9]+)_([0-9]+))') # group 3
    neighbor_pattern = re.compile (r'neighbor (\d+\.\d+\.\d+\.\d+)') # group 1
    neighbor_ipv6_pattern = re.compile (r'neighbor (\w+\:\w+\:\w+\:\w+\:\w+\:\w+\:\w+\:\w+)') # group 1
    md5_pattern = re.compile (r'authentication-key "(.+)"') # group 1
    as_ce_pattern = re.compile (r'peer-as (.\d+)') # group 1
    vpn_max_prefixes_pattern = re.compile (r'maximum (.\d+)') # group 1
    soo_pattern = re.compile (r'community soo-(\d+)_(\d+) members origin:(\d+:\d+)') # group 1 (vpn_id) #group 2 (admin) #group 3 (community)
    vpn_description_pattern = re.compile (r'routing-instances .* description "(\w.+)"') #group 1

    #QoS

    shared_bandwidth_pattern = re.compile (r'cos_input_(\d+)') #group 1 (admin)
    shaping_rate_pattern = re.compile (r'shaping-rate (\d+.)') #group 1
    bronze_rate_pattern = re.compile (r'class_bronze.*transmit-rate (\d+.)') #group 1
    silver_rate_pattern = re.compile (r'class_silver.*transmit-rate (\d+.)') #group 1
    gold_rate_pattern = re.compile (r'class_gold.*transmit-rate (\d+.)') #group 1
    platinum_rate_pattern = re.compile (r'class_platinum.*transmit-rate (\d+.)') #group 1
    video_rate_pattern = re.compile (r'class_video.*transmit-rate (\d+.)') #group 1
    voice_rate_pattern = re.compile (r'class_voice.*transmit-rate (\d+.)') #group 1
    nc_rate_pattern = re.compile (r'class_nc.*transmit-rate (\d+.)') #group 1
    burst_total_pattern = re.compile (r'6CoS_total_.*burst-size-limit (\d+.)') #group 1
    burst_voice_pattern = re.compile (r'6CoS_Prec5_.*burst-size-limit (\d+.)') #group 1
    bronze_percent_pattern = re.compile (r'class_bronze.*percent (\d+)') #group 1
    silver_percent_pattern = re.compile (r'class_silver.*percent (\d+)') #group 1
    gold_percent_pattern = re.compile (r'class_gold.*percent (\d+)') #group 1
    platinum_percent_pattern = re.compile (r'class_platinum.*percent (\d+)') #group 1
    video_percent_pattern = re.compile (r'class_video.*percent (\d+)') #group 1
    voice_percent_pattern = re.compile (r'class_voice.*percent (\d+)') #group 1
    nc_percent_pattern = re.compile (r'class_nc.*percent (\d+)') #group 1
    bfd_minimum_interval_pattern = re.compile (r'routing-instances (vpn_\d+_\d+) protocols bgp group CUSTOMER neighbor (\d+\.\d+\.\d+\.\d+) bfd-liveness-detection (minimum-interval) (\d+)') #group 1 (vpn) #group 2 (neighbor) #group 3 (minimum interval) #group 4 (interval)
    bfd_multiplier_pattern = re.compile (r'routing-instances (vpn_\d+_\d+) protocols bgp group CUSTOMER neighbor (\d+\.\d+\.\d+\.\d+) bfd-liveness-detection (multiplier) (\d+)') #group 1 (vpn) #group 2 (neighbor) #group 3 (minimum interval) #group 4 (interval)
    as_override_pattern = re.compile (r'routing-instances (vpn_\d+_\d+) protocols bgp group CUSTOMER neighbor (\d+\.\d+\.\d+\.\d+) (as-override)') #group 1 (vpn) #group 2 (neighbor) #group 3 (as_override)

    interface_match = interface_pattern.search(output)
    interface_number_match = interface_pattern.search(output)
    unit_match = unit_pattern.search(output)
    description_full_match = description_full_pattern.search(output)
    c_tag_match = c_tag_pattern.search(output)
    s_tag_match = s_tag_pattern.search(output)
    vlan_id_match = vlan_id_pattern.search(output)
    ipv4_address_match = ipv4_address_pattern.search(output)
    mask_match = mask_pattern.search(output)
    mtu_match = mtu_pattern.search(output)
    ipv6_address_match = ipv6_address_pattern.search(output)
    ipv6_mask_match = ipv6_mask_pattern.search(output)
    vpn_name_match = vpn_name_pattern.search(output)
    as_vpn_id_match = as_vpn_id_pattern.search(output)
    vpn_id_match = vpn_id_pattern.search(output)
    internal_vpn_id_match = internal_vpn_id_pattern.search(output)
    ip_loopback_pe_match = ip_loopback_pe_pattern.search(output)
    admin_number_match = admin_number_pattern.search(output)
    as_ce_match = as_ce_pattern.search(output)
    md5_match = md5_pattern.search(output)
    vpn_max_prefixes_match = vpn_max_prefixes_pattern.search(output)
    soo_match = soo_pattern.search(output)
    vpn_description_match = vpn_description_pattern.search(output)
    shaping_rate_match = shaping_rate_pattern.search(output)
    bronze_rate_match = bronze_rate_pattern.search(output)
    silver_rate_match = silver_rate_pattern.search(output)
    gold_rate_match = gold_rate_pattern.search(output)
    platinum_rate_match = platinum_rate_pattern.search(output)
    video_rate_match = video_rate_pattern.search(output)
    voice_rate_match = voice_rate_pattern.search(output)
    nc_rate_match = nc_rate_pattern.search(output)
    burst_total_match = burst_total_pattern.search(output)
    burst_voice_match = burst_voice_pattern.search(output)
    bronze_percent_match = bronze_percent_pattern.search(output)
    silver_percent_match = silver_percent_pattern.search(output)
    gold_percent_match = gold_percent_pattern.search(output)
    platinum_percent_match = platinum_percent_pattern.search(output)
    video_percent_match = video_percent_pattern.search(output)
    voice_percent_match = voice_percent_pattern.search(output)
    nc_percent_match = nc_percent_pattern.search(output)
    bfd_minimum_interval_match = bfd_minimum_interval_pattern.search(output)
    bfd_multiplier_match = bfd_multiplier_pattern.search(output)
    as_override_match = as_override_pattern.search(output)
    shared_bandwidth_match = shared_bandwidth_pattern.search(output)

    #### Neighbor ipv4

    neighbors_ipv4 = re.findall(neighbor_pattern, output)

    if neighbors_ipv4:
        neighbors = set(neighbors_ipv4)
        last_octet_my_ip = int(ipv4_address_match.group(1).split('.')[-1])
        before_last_octet_my_ip = int(ipv4_address_match.group(1).split('.')[-2])
        result = [
            neighbor for neighbor in neighbors 
            if int(neighbor.split('.')[-2]) == before_last_octet_my_ip and int(neighbor.split('.')[-1]) in { last_octet_my_ip -1, last_octet_my_ip +1} 
        ]

        neighbor_match = result[0]
    else:
        neighbor_match = ""

    #### Neighbor ipv6

    neighbor_ipv6 = re.findall(neighbor_ipv6_pattern, output)

    if neighbor_ipv6:
        
        neighbors_ipv6 = set(neighbor_ipv6)

        ipv6_blocks = ipv6_address_match.group(1).split(':')
        last_block_my_ip_ipv6 = int(ipv6_blocks[-1], 16)
        before_last_block_my_ip_ipv6 = int(ipv6_blocks[-2], 16)

        result_ipv6 = [
            neighbor_ipv6 for neighbor_ipv6 in neighbors_ipv6 
            if int(neighbor_ipv6.split(':')[-2], 16) == before_last_block_my_ip_ipv6 and int(neighbor_ipv6.split(':')[-1], 16) in {last_block_my_ip_ipv6 - 1, last_block_my_ip_ipv6 + 1}
        ]

        neighbor_ipv6_match = result_ipv6[0]
    else:
        neighbor_ipv6_match = ""

    ### Site of origin

    soo_name = re.findall(soo_pattern, output)

    if soo_name:

        soo_list = list(set(soo_name))

        vpn = vpn_id_match.group(3)
        admin = admin_number_match.group(9)

        for soo in soo_list:
            if soo[0] == vpn and soo[1] == admin:
                soo_community_match = soo[2]
    else:
        soo_community_match = ""

    ### BFD

    bfd_minimum_interval_pattern = re.findall(bfd_minimum_interval_pattern, output)

    if bfd_minimum_interval_pattern:

        bfd_list = list(set(bfd_minimum_interval_pattern))

        vpn_name_bfd = vpn_name_match.group(1)

        for bfd in bfd_list:
            if bfd[0] == vpn_name_bfd and bfd[1] == neighbor_match and bfd[2] == 'minimum-interval':
                bfd_minimum_interval_match = bfd[3]
    else:
        bfd_minimum_interval_match = ""

    bfd_multiplier_pattern = re.findall(bfd_multiplier_pattern, output)

    if bfd_multiplier_pattern:

        bfd_multiplier_list = list(set(bfd_multiplier_pattern))

        vpn_name_bfd = vpn_name_match.group(1)

        for bfd in bfd_multiplier_list:
            if bfd[0] == vpn_name_bfd and bfd[1] == neighbor_match and bfd[2] == 'multiplier':
                bfd_multiplier_match = bfd[3]

    else:
        bfd_multiplier_match = ""

    ### AS-OVERRIDE

    as_override_pattern = re.findall(as_override_pattern, output)

    if as_override_pattern:

        as_override_list = list(set(as_override_pattern))

        vpn_name_as_override = vpn_name_match.group(1)

        for as_override in as_override_list:
            if as_override[0] == vpn_name_as_override and as_override[1] == neighbor_match and as_override[2] == 'as-override':
                as_override_match = True

    else:
        as_override_match = ""

    ### SHARED-BANDWIDTH

    shared_bandwidth_pattern = re.findall(shared_bandwidth_pattern, output)

    if shared_bandwidth_pattern:
        shared_bandwidth_list = list(set(shared_bandwidth_pattern))
        vpn_shared_bandwidth = shared_bandwidth_match.group(1)
        for shared_bandwidth in shared_bandwidth_list:
            if shared_bandwidth == admin_number_match.group(9):
                shared_bandwidth_match = True
    else:
        shared_bandwidth_match = ""
    
    fieldnames = [
        "SHARED_BANDWIDTH",
        "INTERFACE",
        "INTERFACE_ID_NUMBER",
        "SUBINTERFACE_ID_PE",
        "DESCRIPTION",
        "VLAN_ID",
        "C_TAG_PE",
        "S_TAG_PE",
        "IP_WAN_PE",
        "IP_WAN_MASK",
        "MTU",
        "IP_WAN_CE",
        "IPv6_WAN_PE",
        "IPv6_WAN_MASK",
        "IPv6_WAN_CE",
        "VPN_NAME",
        "VPN_DESCRIPTION",
        "AS_VPN",
        "VPN_ID",
        "INTERNAL_VPN_ID",
        "IP_LOOPBACK_PE",
        "ADMIN_NUMBER",
        "AS_CE",
        "ID_SITE_COMMUNITY",
        "MD5",
        "MAXIMUM_PREFIXES",
        "AS_OVERRIDE",
        "MINIMUM-INTERVAL",
        "MULTIPLIER",
        "TOTAL_DOWN_BANDWIDTH_B",
        "TOTAL_BURST",
        "BRONZE_DOWN_BANDWIDTH_B",
        "SILVER_DOWN_BANDWIDTH_B",
        "GOLD_DOWN_BANDWIDTH_B",
        "PLATINUM_DOWN_BANDWIDTH_B",
        "VIDEO_DOWN_BANDWIDTH_B",
        "VOICE_DOWN_BANDWIDTH_B",
        "MANAGE_BANDWIDTH_B",
        "VOICE_BURST",
        "BRONZE_BW_PERC",
        "SILVER_BW_PERC",
        "GOLD_BW_PERC",
        "PLATINUM_BW_PERC",
        "VIDEO_BW_PERC",
        "VOICE_BW_PERC",
        "MANAGE_BW_PERC"
    ]

    variables = {
            "SHARED_BANDWIDTH": shared_bandwidth_match if 'shared_bandwidth_match' in locals() and shared_bandwidth_match else "",
            "INTERFACE": interface_match.group(1) if 'interface_match' in locals() and interface_match else "",
            "INTERFACE_ID_NUMBER": interface_match.group(3) if 'interface_match' in locals() and interface_match else "",
            "SUBINTERFACE_ID_PE": unit_match.group(1) if 'unit_match' in locals() and unit_match else "",
            "DESCRIPTION": description_full_match.group(1) if 'description_full_match' in locals() and description_full_match else "",
            "VLAN_ID": vlan_id_match.group(1) if 'vlan_id_match' in locals() and vlan_id_match else "",
            "C_TAG_PE": c_tag_match.group(1) if 'c_tag_match' in locals() and c_tag_match else "",
            "S_TAG_PE": s_tag_match.group(1) if 's_tag_match' in locals() and s_tag_match else "",
            "IP_WAN_PE": ipv4_address_match.group(1) if 'ipv4_address_match' in locals() and ipv4_address_match else "",
            "IP_WAN_MASK": mask_match.group(2) if 'mask_match' in locals() and mask_match else "",
            "MTU": mtu_match.group(1) if 'mtu_match' in locals() and mtu_match else "",
            "IP_WAN_CE": neighbor_match if 'neighbor_match' in locals() else "",
            "IPv6_WAN_PE": ipv6_address_match.group(1) if 'ipv6_address_match' in locals() and ipv6_address_match else "",
            "IPv6_WAN_MASK": ipv6_mask_match.group(2) if 'ipv6_mask_match' in locals() and ipv6_mask_match else "",
            "IPv6_WAN_CE": neighbor_ipv6_match if 'neighbor_ipv6_match' in locals() else "",
            "VPN_NAME": vpn_name_match.group(1) if 'vpn_name_match' in locals() and vpn_name_match else "",
            "VPN_DESCRIPTION": vpn_description_match.group(1) if 'vpn_description_match' in locals() and vpn_description_match else "",
            "AS_VPN": as_vpn_id_match.group(2) if 'as_vpn_id_match' in locals() and as_vpn_id_match else "",
            "VPN_ID": vpn_id_match.group(3) if 'vpn_id_match' in locals() and vpn_id_match else "",
            "INTERNAL_VPN_ID": internal_vpn_id_match.group(2) if 'internal_vpn_id_match' in locals() and internal_vpn_id_match else "",
            "IP_LOOPBACK_PE": ip_loopback_pe_match.group(1) if 'ip_loopback_pe_match' in locals() and ip_loopback_pe_match else "",
            "ADMIN_NUMBER": admin_number_match.group(9) if 'admin_number_match' in locals() and admin_number_match else "",
            "AS_CE": as_ce_match.group(1) if 'as_ce_match' in locals() and as_ce_match else "",
            "ID_SITE_COMMUNITY": soo_community_match if 'soo_community_match' in locals() else "",
            "MD5": md5_match.group(1) if 'md5_match' in locals() and md5_match else "",
            "MAXIMUM_PREFIXES": vpn_max_prefixes_match.group(1) if 'vpn_max_prefixes_match' in locals() and vpn_max_prefixes_match else "",
            "AS_OVERRIDE": as_override_match if 'as_override_match' in locals() else "",
            "MINIMUM-INTERVAL": bfd_minimum_interval_match if 'bfd_minimum_interval_match' in locals() else "",
            "MULTIPLIER": bfd_multiplier_match if 'bfd_multiplier_match' in locals() else "",
            "TOTAL_DOWN_BANDWIDTH_B": shaping_rate_match.group(1) if 'shaping_rate_match' in locals() and shaping_rate_match else "",
            "TOTAL_BURST": burst_total_match.group(1) if 'burst_total_match' in locals() and burst_total_match else "",
            "BRONZE_DOWN_BANDWIDTH_B": bronze_rate_match.group(1) if 'bronze_rate_match' in locals() and bronze_rate_match else "",
            "SILVER_DOWN_BANDWIDTH_B": silver_rate_match.group(1) if 'silver_rate_match' in locals() and silver_rate_match else "",
            "GOLD_DOWN_BANDWIDTH_B": gold_rate_match.group(1) if 'gold_rate_match' in locals() and gold_rate_match else "",
            "PLATINUM_DOWN_BANDWIDTH_B": platinum_rate_match.group(1) if 'platinum_rate_match' in locals() and platinum_rate_match else "",
            "VIDEO_DOWN_BANDWIDTH_B": video_rate_match.group(1) if 'video_rate_match' in locals() and video_rate_match else "",
            "VOICE_DOWN_BANDWIDTH_B": voice_rate_match.group(1) if 'voice_rate_match' in locals() and voice_rate_match else "",
            "MANAGE_BANDWIDTH_B": nc_rate_match.group(1) if 'nc_rate_match' in locals() and nc_rate_match else "",
            "VOICE_BURST": burst_voice_match.group(1) if 'burst_voice_match' in locals() and burst_voice_match else "",
            "BRONZE_BW_PERC": bronze_percent_match.group(1) if 'bronze_percent_match' in locals() and bronze_percent_match else "",
            "SILVER_BW_PERC": silver_percent_match.group(1) if 'silver_percent_match' in locals() and silver_percent_match else "",
            "GOLD_BW_PERC": gold_percent_match.group(1) if 'gold_percent_match' in locals() and gold_percent_match else "",
            "PLATINUM_BW_PERC": platinum_percent_match.group(1) if 'platinum_percent_match' in locals() and platinum_percent_match else "",
            "VIDEO_BW_PERC": video_percent_match.group(1) if 'video_percent_match' in locals() and video_percent_match else "",
            "VOICE_BW_PERC": voice_percent_match.group(1) if 'voice_percent_match' in locals() and voice_percent_match else "",
            "MANAGE_BW_PERC": nc_percent_match.group(1) if 'nc_percent_match' in locals() and nc_percent_match else ""
        }

    return variables, fieldnames