"""
One-time script to seed state/known_repos.json from the existing provenance data.

Run once:  python seed_known_repos.py
"""

from state import save_known_repos

# The 23 sources (A-W) already catalogued in the SigilYX SPECIFICATION-E2.md.
# We record them here so scan.py won't re-download files we already have.
# SHA is set to "seed" - the next scan will see it differs from the real HEAD
# and re-enumerate, but will skip download for any file whose sha256 is already
# tracked.  Set "last_checked_sha" to None and the scanner will treat them as
# needing a fresh check on first real run.

KNOWN: dict = {
    "habramsohn/MSBA-Portfolio": {
        "last_checked_sha": "ba264c63d0c49749dd9e14513dbb41e684f62280",
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Analytics/EHR Data Transformation.yxzp!/Task1Output.yxdb", "size": 1110866, "sha256": "28E62A8DEA1355F387A7CF89EECF384886C154AFA211978BDE2577BD3FE1EA05"},
            {"path": "Analytics/EHR Data Transformation.yxzp!/Task2Output.yxdb", "size": 222070, "sha256": "7DFB79432FDE920670425606F24229AFD713E82E165875469814CD917FAF76C3"},
            {"path": "Analytics/EHR Data Transformation.yxzp!/Task3Output.yxdb", "size": 318764, "sha256": "7AB36DB86D50B3AEC6EC6620A3098A8C8B1A9FE031DD7B87359E4D3816CEA66F"},
        ],
        "e1_file_count": 2,
        "skipped": False,
    },
    "AkimasaKajitani/AdventOfCode": {
        "last_checked_sha": "658bdc3a3ffc18e436bd4816259ba8adee3b9e47",
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "2015/Day01/2015_01_input.yxdb", "size": 3138, "sha256": "D2D8F5DBC5F5A0215AA91837E5271FD611752BA34BBAF9A0CF407D294F427212"},
            {"path": "2015/Day02/2015_02_input.yxdb", "size": 5333, "sha256": "1BF4947C9D3B778025BDF986CE201B10DB5DD7A058D6C079FEE3888898CAF516"},
            {"path": "2015/Day03/2015_03_input.yxdb", "size": 4512, "sha256": "81BCCEB50F035BCE9048DAC978FF6937314498189EF01935B684BD035AEEA3FB"},
            {"path": "2015/Day04/2015_04_input.yxdb", "size": 455, "sha256": "FF0DA08C460430459EAFE2B66ACFDE9BED1F72A410958B8E700AA2E2484CAB72"},
            {"path": "2015/Day05/2015_05_input.yxdb", "size": 17451, "sha256": "EB40DADC09A9FB001F68361629849A43F9C6E146F8E4C3E899E6573454F0064F"},
            {"path": "2015/Day07/2015_07_input.yxdb", "size": 3744, "sha256": "6F245C6006146B6092D62FFA7288F9023A26D25D8982029B3A85891F1EFCCCA8"},
            {"path": "2015/Day07/temp.yxdb", "size": 4527, "sha256": "02C9D50F1EAE95E43D40F61DED50519D6C950D574D21B534FB6125FCC33382A2"},
            {"path": "2015/Day09/2015_09_input.yxdb", "size": 770, "sha256": "16B107369B9FBF224262C33B2058BEBBC544F080D7627C7926DF48B14852DEE1"},
            {"path": "2015/Day10/2015_10_input.yxdb", "size": 457, "sha256": "287535BB27E00E7D0CBD24D729AE470E92C87152E612F6327E49FDBAE91C03C6"},
            {"path": "2015/Day11/2015_11_input.yxdb", "size": 455, "sha256": "9A5C20336E88675D9D1E97FA485B7ADA9BB08CFEBF26354E82E455403099757B"},
            {"path": "2015/Day12/2015_12_input.yxdb", "size": 16980, "sha256": "C049C9DD2A974F64E4039EE2D07A32031E213E4360A2B9B1D8A1638980DF6319"},
            {"path": "2015/Day13/2015_13_input.yxdb", "size": 1138, "sha256": "D91C428AA437F43ABA8A1CE35E4326A17C96D31C322C9EA8D248856C579340A4"},
            {"path": "2015/Day14/2015_14_input.yxdb", "size": 725, "sha256": "4756878F100BC77C0EDCA1FB476AB3EF4F1E4C675D71D0F1B2323ABA67A458EC"},
            {"path": "2015/Day15/2015_15_input.yxdb", "size": 658, "sha256": "B3A58EE7257401DCCE83E7358A21F209EA3A7B8ABD5A49A603FAA08DD986FC84"},
            {"path": "2015/Day16/2015_16_input.yxdb", "size": 7104, "sha256": "14F28DCEE75C7A4034F9ABA0B611FDC84EB57CFB0DA2C9EEF4458F3BDCD66E0C"},
            {"path": "2015/Day17/2015_17_input.yxdb", "size": 506, "sha256": "540EF104D278C44E15092648F6C3A110D1D67AC606435A74907F945E4EB3DD37"},
            {"path": "2015/Day18/2015_18_input.yxdb", "size": 4577, "sha256": "404AD05087E099CA159D4190A30C5E6A7DE9314228A68A30FE6FBC5331230992"},
            {"path": "2015/Day19/2015_19_input.yxdb", "size": 1028, "sha256": "B73E29E96B9A18584B586EEBFAB87E32D0A3C60967054F1E3C1085B2139714A5"},
            {"path": "2015/Day20/2015_20_input.yxdb", "size": 455, "sha256": "EB5EB3BDB94FB4924BC9750BFB9D96C6C77D498A3AEA9C77835277475483B6F9"},
            {"path": "2024/Day01/2024_01_input.yxdb", "size": 10744, "sha256": "A2D882C35B0F192644BA98D686F38B85FD037673192E2B9C38D736422F28D731"},
            {"path": "2024/Day02/2024_02_input.yxdb", "size": 11627, "sha256": "5C5FE77A32CA58BE9316AD1482E847128971C5E4F9F8E7697667E6E7C29745F9"},
            {"path": "2024/Day03/2024_03_input.yxdb", "size": 13196, "sha256": "69627FC6EFF02E0B9833A39B0C267BD21C8E72DED18F03B793982048CA3A3DE0"},
            {"path": "2024/Day04/2024_04_input.yxdb", "size": 10097, "sha256": "64BBD6F6BA868F8834BBB696A48F392D37B8BECCF7ED0F8F18FC085699D7916B"},
            {"path": "2024/Day05/2024_05_input.yxdb", "size": 9949, "sha256": "AAA9431B97D7EAFF96730F4D115BE3B522CDDE8B0E0584955E249F5D014695EA"},
            {"path": "2024/Day06/2024_06_input.yxdb", "size": 3310, "sha256": "29E529806D58E85909D6914B7A794BEE3530325B9E51590874078665348AF8E8"},
            {"path": "2024/Day07/2024_07_input.yxdb", "size": 20261, "sha256": "E06A6CA47B29CAF57994F3B306B448FD5634D0FDC5517C988A64EEA2939288FB"},
            {"path": "2024/Day08/2024_08_input.yxdb", "size": 1131, "sha256": "12FDB6C209CC869A9A725FE80FB6947C06D441C40F3C89D8C0B12D6AF841B607"},
            {"path": "2024/Day09/2024_09_input.yxdb", "size": 18100, "sha256": "7915381A197D34AB36A171BDC3193B05FE5B9BC5F18D55C4BE7CA02DA2FC2FFA"},
            {"path": "2024/Day09/temp.yxdb", "size": 210153, "sha256": "BAEEC5EFF8C7702B0D944151F06D75B27391196FB1C84AFCE73F41CB5D81117D"},
            {"path": "2024/Day10/2024_10_input.yxdb", "size": 3019, "sha256": "96DD999AB7B624F1C51684F9F51EE8D5E3F66D3313AC98F81FD23DF0A9407A95"},
            {"path": "2024/Day10/temp1.yxdb", "size": 3979, "sha256": "047C97BDC17E74181D00847C30E9ED4786D3ED18FD2EB0F81D6B6335A7C1F495"},
            {"path": "2024/Day10/temp2.yxdb", "size": 19984, "sha256": "7ECA4C3CB1EEB0AD8E174989DD795D4F7B4127A828A549A8F45CC87162EC320E"},
            {"path": "2024/Day11/2024_11_input.yxdb", "size": 595, "sha256": "0427426B2627648311D7860744AA01BA484A0F78C9061AE749C5FFE518ECAB44"},
            {"path": "2024/Day12/2024_12_input.yxdb", "size": 8931, "sha256": "41586F7612A7D27B84375E6162536CF5A483855EA0CC200AAEF2B12C60D4EADC"},
            {"path": "2024/Day13/2024_13_input.yxdb", "size": 8332, "sha256": "58FFA514CD66E6562C309E515A8D019B4BE557299E303DA85697A4E4BE60E764"},
            {"path": "2024/Day14/2024_14_input.yxdb", "size": 5799, "sha256": "083CBEFE11509F0A08B174FC51CBED8D10F5BDC0C5E5BD71F0BA5624EC919FB3"},
            {"path": "2024/Day15/2024_15_input.yxdb", "size": 11116, "sha256": "4F1B1DEA78920C999176D63266789654717663FE88083D53284FA87779EF7D65"},
            {"path": "2024/Day15/ForP2Macro1.yxdb", "size": 81096, "sha256": "3A30F216B753E3ADE2F15AF6F802D6567327335EF14BDE0CD1BA50F6A368CF5E"},
            {"path": "2024/Day15/ForP2macro_2.yxdb", "size": 14173, "sha256": "B1D89869879C269654C0407EBBDA06B01F3453DE8D5A7E4407A30982E8FB8F12"},
            {"path": "2024/Day16/2024D16P1_dijk.yxdb", "size": 2829, "sha256": "56F908509118B791DBF1BCA568FE445EA4386DD1B3D46102A56E295236AA90D1"},
            {"path": "2024/Day16/2024D16P1_dijk_p2.yxdb", "size": 60801, "sha256": "E9943C3FDA1B4E3F696FE2FAD76DBCFE9A5E8784C7996A9E23BAD1980EA26171"},
            {"path": "2024/Day16/2024D16P1_dijk_p2_e.yxdb", "size": 1958, "sha256": "37EF36B660A65DE4897D4C8C398E51E22D8DDF913CA798AAB7F565E03BCB1DAE"},
            {"path": "2024/Day16/2024_16_input.yxdb", "size": 7389, "sha256": "185D1AA9C29C0FFD32D9396010D23CBCC2076E2645ED393FF2BDB6ACA345C177"},
            {"path": "2024/Day16/P2_SearchNodes.yxdb", "size": 6080, "sha256": "F7EAF44AEF0B3269F07CB5C0BE05E6D6EA7CAC17DD5AB2E413E857E6413C7238"},
            {"path": "2024/Day16/P2_edgelist.yxdb", "size": 92770, "sha256": "5DF1743CFCC2E4D67FE6949D7DF01F82BE71B56BF2ADE05951DD38A25EC99A94"},
            {"path": "2024/Day17/2024_17_input.yxdb", "size": 525, "sha256": "CAA39753763E3987A993E6B4084416666300B612AAE67DA26FFFA42511472B0C"},
            {"path": "2024/Day18/2024_18_input.yxdb", "size": 13308, "sha256": "FE52C8565C9368F8F54DD07DDDA4805965CB11BD16625A432011D960CF403EBE"},
            {"path": "2024/Day19/2024_19_input.yxdb", "size": 13916, "sha256": "B834D2100D6DE6BCA047FC368AFA95CB4E1388B4C418A40813E0786E88967925"},
            {"path": "2024/Day20/2024_20_input.yxdb", "size": 6944, "sha256": "005D32F0A1C768CBAE8759BD783E3C272D645A4277AA30C5980C824FB9A1C604"},
            {"path": "2024/Day21/D21P2_ite_input.yxdb", "size": 620, "sha256": "20EAD3D7394F1C960F225CF403495D418ABBA020044180ACF6B30A4ECDF4C56F"},
            {"path": "2024/Day21/P1_input.yxdb", "size": 535, "sha256": "C3991569F65F1558E138B9ECDCD269D9A29EB07A18A5FC6654EF93346A40AEF6"},
            {"path": "2024/Day22/2024_22_input.yxdb", "size": 18085, "sha256": "18B15BA5BF3648A5E0A07B3F4D0D0C0A4EBB4576B98874BB4F3975FFBBAA5B45"},
            {"path": "2024/Day23/2024_23_input.yxdb", "size": 19595, "sha256": "6932356A4490E77039DEF43FDFFBECAF1802B0AD3FE09219C2E1589EF5544FAB"},
            {"path": "2024/Day23/day23_1.yxdb", "size": 338, "sha256": "02B28823218FF7637CBCEC3FE6145527BBCA18725AB88DC0989A6653932C5F17"},
            {"path": "2024/Day23/day23_2.yxdb", "size": 39164, "sha256": "DD016F78E6D2EACAB67CC973EE0F59470AF5A4ACFBECA78E8EDE6D5E0437F363"},
            {"path": "2024/Day24/2024_24_input.yxdb", "size": 3870, "sha256": "1E42843ED5A561046D83AE429D089E53570BDC5DE8B6C5645C10A0BD8D444D3D"},
            {"path": "2024/Day25/2024_25_input.yxdb", "size": 7792, "sha256": "389CC48715DCD494DBD5EE5C7F5285B4AAD59F79B6A993C36D50C8209A3E95D1"},
            {"path": "2025/Day01/2025_01_input.yxdb", "size": 10556, "sha256": "315CABEA2E0C1433726248C644E270AFC0C9D554FFDC3AB0FC0A7F229C62D847"},
            {"path": "2025/Day02/2025_02_input.yxdb", "size": 893, "sha256": "3461E5469CC3F5223DF52466F88C2DD1EB20CF3B06A9EF200AB4B2A39DC20006"},
            {"path": "2025/Day03/2025_03_input.yxdb", "size": 14250, "sha256": "CCCCFF2C5E2AABE250BF8D21EC329F9B79F1E76F91087BEAF04249D62FE8BF4C"},
            {"path": "2025/Day05/2025_05_input.yxdb", "size": 19239, "sha256": "C3284B36A210B9AE2D0DD5948C77FB127937D9A7E778DDDBD792957F56914FF1"},
            {"path": "2025/Day06/2025_06_input_actual.yxdb", "size": 12389, "sha256": "8AD6F216EF4B2460C16AFCBD047EF173270DBC89FB223E603CFF916133AE2A92"},
            {"path": "2025/Day07/2025_07_input_actual.yxdb", "size": 3066, "sha256": "B85DFE922028B0759AA039BA4DA3E1A2D717B757AE75A0E9FFFB9F1ADDDE5A65"},
            {"path": "2025/Day08/2025_08_input_actual.yxdb", "size": 16809, "sha256": "4D2489FA47306F64C80D187D4DC4609E0C7F54D2DEB2A3E48CC5503D490FBDEB"},
        ],
        "e1_file_count": 1,
        "skipped": False,
    },
    "PacktPublishing/Alteryx-Designer-Cookbook": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "ch3/Recipe2/DATA/CityBike_extract.yxdb", "size": 3744623, "sha256": "8A578CF741075E25DF184BCD3EB5BFAE3EFFA1F5E8835E95A01AE240212B41D2"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "PacktPublishing/Data-Engineering-with-Alteryx": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Chapter 06/Data/places_child.yxdb", "size": 1204, "sha256": "4B69D667A6D262B6BD992A90BF8500C9C56C3A047F71F9DEC3D5EFB0C4E4E474"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "SaudAzmi/airport-alteryx-workflow": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Output/Airport_city_population.yxdb", "size": 159410, "sha256": "CFB9789ABBEE56D3DEA244F58C8DCE6FCB9992175017F34E6EB1A8E7A9E85BA3"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "AltonDsouza/Alteryx-Challenge-482-": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Challenge482_start_file/Outputs/Q3_Answer.yxdb", "size": 0, "sha256": ""},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "liyengL/Alteryx_challenges": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-16T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Movie.yxzp!/Input335.yxdb", "size": 0, "sha256": ""},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "ABANISINGHA/Alteryx_workflows": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": "unknown", "size": 0, "sha256": ""}],
        "e1_file_count": 0,
        "skipped": False,
    },
    "ChrisDataBlog/Alteryx-Inspire-2023---Design-Patterns-for-Testing": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": "unknown", "size": 0, "sha256": ""}],
        "e1_file_count": 0,
        "skipped": False,
    },
    "FL-Marine/Alteryx-Work-Flows": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": f"e2_file_{i}", "size": 0, "sha256": ""} for i in range(9)],
        "e1_file_count": 0,
        "skipped": False,
    },
    "KOdoi-OJ/Capstone-Project-Combining-Predictive-Techniques": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": f"e2_file_{i}", "size": 0, "sha256": ""} for i in range(2)],
        "e1_file_count": 0,
        "skipped": False,
    },
    "MOHAMMADALI230/NovaKart-Profitability-Analytics": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": f"e2_file_{i}", "size": 0, "sha256": ""} for i in range(3)],
        "e1_file_count": 0,
        "skipped": False,
    },
    "Satvikp546/Alteryx_Workflows": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": "unknown", "size": 0, "sha256": ""}],
        "e1_file_count": 0,
        "skipped": False,
    },
    "SeanAdams10/AdventOfCodePython": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": f"e2_file_{i}", "size": 0, "sha256": ""} for i in range(7)],
        "e1_file_count": 0,
        "skipped": False,
    },
    "Sivivatu/Alteryx-Weekly-Challenge": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": "unknown", "size": 0, "sha256": ""}],
        "e1_file_count": 0,
        "skipped": False,
    },
    "Szymon-Czuszek/Alteryx-Weekly-Challenges": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": f"e2_file_{i}", "size": 0, "sha256": ""} for i in range(6)],
        "e1_file_count": 0,
        "skipped": False,
    },
    "afnfyz/alteryx_weekly_challenge_filter": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [{"path": f"e2_file_{i}", "size": 0, "sha256": ""} for i in range(3)],
        "e1_file_count": 0,
        "skipped": False,
    },
    "joshuaburkhow/adventofcode": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Day9part1.yxdb", "size": 4405, "sha256": "A8EEEE98A608FD1E181C3662C02C78884A05E807D02B580ACACC90E052F03556"},
            {"path": "Day9part2.yxdb", "size": 5252, "sha256": "140005F71950F0587BED4DE043F2C2DC0EA4F601442A15FFAD3DD82B3258DCE5"},
            {"path": "tmpIterator - Copy.yxdb", "size": 648, "sha256": "ECE2FE70519B4F8C79915437B396751A3AAF606EB083B8135F4E8EB454E39972"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "kumarritik24/Sales-Performance-Optimization-DC-Industries": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Order Data Complete_backup.yxdb", "size": 47203, "sha256": "C07530FE89C5B1EE572EB66DD57998247176DD79070EEFBA3FE869B6270D7C1F"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "mishramayank24/predicitve_analytics_using_ALTERYX": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "cluster task1 output.yxdb", "size": 5348, "sha256": "0AD2C3ED864FD2014F602D4BDE75483F7FEE3F036B3DD14554FFAF97ABC3E9C0"},
            {"path": "new store cluster.yxdb", "size": 621, "sha256": "CBA941F4C634071A81AB9C41F36374AE5A19C66075E299FD139124B4A09900CC"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "sarincr/Data-Analytics-with-Alteryx": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "MultiOut.yxdb", "size": 7564258, "sha256": "E9F99982CA88C67AF53B53DDCEE2EAAFF5994F47470AF3E5D4A772C47026F0DD"},
            {"path": "Out1.yxdb", "size": 1536884, "sha256": "56C8235C4DC118ABCF89AC144814DBC6DC9EC0D7E8A2EBF29F1F68B6BC67A927"},
            {"path": "Out2.yxdb", "size": 3794773, "sha256": "04E773A4212388CBFF882102D0B77E16C1C38C47F895EA4CE2CA24226C00A7C5"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "ziadasal/alteryx-mini-projects": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "Output_Task1.yxdb", "size": 1023883, "sha256": "27504E50AFF8FC3A70C04689DE4E5C97493A1F2DC60A601C7FAF1749C7F16740"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
    "zulekhapathan/Customer-orders-Workflow-using-Alteryx-designer": {
        "last_checked_sha": None,
        "last_checked_at": "2026-03-17T00:00:00Z",
        "default_branch": "main",
        "e2_files": [
            {"path": "order_items.yxdb", "size": 29227, "sha256": "80749E132037AB6449B1EA51F5F4E52D1AE3013AB2DC2C0B661B5133E07D8D1E"},
            {"path": "orders.yxdb", "size": 23149, "sha256": "EF80391E108626D4B2329D7E01EF594308A37A9990F1AB59B30E68D6AB2AE100"},
        ],
        "e1_file_count": 0,
        "skipped": False,
    },
}


def main():
    save_known_repos(KNOWN)
    total_e2 = sum(len(v["e2_files"]) for v in KNOWN.values())
    print(f"Seeded {len(KNOWN)} repos, {total_e2} E2 files tracked.")
    print(f"Written to state/known_repos.json")


if __name__ == "__main__":
    main()
