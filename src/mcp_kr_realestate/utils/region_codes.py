import pandas as pd
from typing import Optional
from mcp_kr_realestate.apis.region_code_api import get_region_codes

def get_region_code_df(per_page: int = 1000, max_page: int = 50) -> pd.DataFrame:
    """
    전체 법정동 코드 목록을 DataFrame으로 반환합니다. (페이지네이션)
    Args:
        per_page (int): 페이지당 데이터 수 (기본 1000)
        max_page (int): 최대 페이지 수 (기본 50)
    Returns:
        pd.DataFrame: 법정동 코드 데이터
    """
    all_data = []
    for page in range(1, max_page + 1):
        resp = get_region_codes(page=page, per_page=per_page)
        if "data" not in resp or not resp["data"]:
            break
        all_data.extend(resp["data"])
        if len(resp["data"]) < per_page:
            break
    return pd.DataFrame(all_data)

def get_lawd_cd_by_name(sido: str, sigungu: Optional[str] = None, eupmyeon: Optional[str] = None) -> Optional[str]:
    """
    시도명, 시군구명, 읍면동명으로 5자리 법정동코드(LAWD_CD)를 반환합니다.
    Args:
        sido (str): 시도명 (예: '서울특별시')
        sigungu (str, optional): 시군구명 (예: '강남구')
        eupmyeon (str, optional): 읍면동명 (예: '역삼동')
    Returns:
        Optional[str]: 5자리 법정동코드 (없으면 None)
    """
    df = get_region_code_df()
    cond = (df["시도명"] == sido)
    if sigungu:
        cond &= (df["시군구명"] == sigungu)
    if eupmyeon:
        cond &= (df["읍면동명"] == eupmyeon)
    row = df[cond].sort_values("순위").head(1)
    if not row.empty:
        code = str(row.iloc[0]["법정동코드"])
        return code[:5]
    return None 