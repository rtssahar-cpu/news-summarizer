from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class Category(StrEnum):
    JP_EQUIPMENT_NEW_DEVELOPMENT = "jp_equipment_new_development"
    CONTRACTOR_MITSUBISHI_HEAVY = "contractor_mitsubishi_heavy"
    CONTRACTOR_KAWASAKI_HEAVY = "contractor_kawasaki_heavy"
    CONTRACTOR_SUBARU = "contractor_subaru"
    CONTRACTOR_IHI = "contractor_ihi"
    CONTRACTOR_MITSUBISHI_ELECTRIC = "contractor_mitsubishi_electric"
    CONTRACTOR_NEC = "contractor_nec"
    CONTRACTOR_FUJITSU = "contractor_fujitsu"
    CONTRACTOR_HITACHI = "contractor_hitachi"
    UNMANNED_UUV = "unmanned_uuv"
    UNMANNED_USV = "unmanned_usv"
    UNMANNED_UGV = "unmanned_ugv"
    UNMANNED_UAV = "unmanned_uav"
    UNMANNED_LOITERING_MUNITION = "unmanned_loitering_munition"
    AIR_DEFENSE_SYSTEM = "air_defense_system"
    AMD_IAMD = "amd_iamd"
    STANDOFF_MISSILE = "standoff_missile"
    ELECTRONIC_WARFARE = "electronic_warfare"
    EARLY_WARNING_AIRCRAFT = "early_warning_aircraft"
    MINISTER_STATEMENT = "minister_statement"
    THREE_DOCUMENTS = "three_documents"


_CONTRACTOR_NAMES: Mapping[Category, str] = MappingProxyType(
    {
        Category.CONTRACTOR_MITSUBISHI_HEAVY: "三菱重工業",
        Category.CONTRACTOR_KAWASAKI_HEAVY: "川崎重工業",
        Category.CONTRACTOR_SUBARU: "SUBARU",
        Category.CONTRACTOR_IHI: "IHI",
        Category.CONTRACTOR_MITSUBISHI_ELECTRIC: "三菱電機",
        Category.CONTRACTOR_NEC: "NEC",
        Category.CONTRACTOR_FUJITSU: "富士通",
        Category.CONTRACTOR_HITACHI: "日立製作所",
    }
)


def _contractor_criterion(company_name: str) -> str:
    return (
        f"{company_name}（グループ会社を含む）の防衛・安全保障・宇宙に関する動き"
        "（受注・研究開発・生産・海外企業との提携等）。民生事業のみの発表は該当しない"
    )


# AIに渡す各カテゴリの判定基準。記事が基準を満たすかは、記事中の明記に加え、
# 機種名等から判断できる場合も該当とする（プロンプト側で指示する）
CATEGORY_CRITERIA: Mapping[Category, str] = MappingProxyType(
    {
        Category.JP_EQUIPMENT_NEW_DEVELOPMENT: (
            "日本の防衛装備品に関する新しい動き（研究開発・試験・契約・調達・配備・輸出等）"
        ),
        **{
            category: _contractor_criterion(company_name)
            for category, company_name in _CONTRACTOR_NAMES.items()
        },
        Category.UNMANNED_UUV: "全長10m以上の無人潜水機（UUV）",
        Category.UNMANNED_USV: "無人水上艇（USV）。大きさは問わない",
        Category.UNMANNED_UGV: "無人地上車両（UGV）。大きさは問わない",
        Category.UNMANNED_UAV: "重量1t以上の無人航空機（UAV）",
        Category.UNMANNED_LOITERING_MUNITION: ("航続距離600km以上の徘徊型弾薬（攻撃ドローン）"),
        Category.AIR_DEFENSE_SYSTEM: (
            "日本の防空システム（地対空・艦対空ミサイル、警戒管制レーダー等）"
        ),
        Category.AMD_IAMD: "AMD（防空・ミサイル防衛）・IAMD（統合防空ミサイル防衛）",
        Category.STANDOFF_MISSILE: (
            "スタンドオフミサイル（陸上・艦艇・航空機のいずれから発射するものも含む）"
        ),
        Category.ELECTRONIC_WARFARE: "電子戦（電子戦機・電子戦装置・電磁波領域の能力等）",
        Category.EARLY_WARNING_AIRCRAFT: "早期警戒機・早期警戒管制機",
        Category.MINISTER_STATEMENT: (
            "現職の防衛大臣、または小野寺五典氏の、防衛装備品に関する発言・動き。"
            "装備品に関係しない動きは該当しない"
        ),
        Category.THREE_DOCUMENTS: (
            "安保3文書（国家安全保障戦略・国家防衛戦略・防衛力整備計画）の"
            "策定・改定・実施に関する動き"
        ),
    }
)
