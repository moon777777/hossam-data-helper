import numpy as np
from tabulate import tabulate
from pandas import DataFrame, Series, read_excel, get_dummies, DatetimeIndex
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, PolynomialFeatures
from sklearn.impute import SimpleImputer
from scipy.stats import normaltest

from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
from statsmodels.stats.outliers_influence import variance_inflation_factor

import sys
from pca import pca
from matplotlib import pyplot as plt

from .core import *


def my_normalize_data(
    mean: float, std: float, size: int = 100, round: int = 2
) -> np.ndarray:
    """정규분포를 따르는 데이터를 생성한다.

    Args:
        mean (float): 평균
        std (float): 표준편차
        size (int, optional): 데이터 크기. Defaults to 1000.

    Returns:
        np.ndarray: 정규분포를 따르는 데이터
    """
    p = 0
    x = []
    while p < 0.05:
        x = np.random.normal(mean, std, size).round(round)
        _, p = normaltest(x)

    return x


def my_normalize_df(
    means: list = [0, 0, 0],
    stds: list = [1, 1, 1],
    sizes: list = [100, 100, 100],
    rounds: int = 2,
) -> DataFrame:
    """정규분포를 따르는 데이터프레임을 생성한다.

    Args:
        means (list): 평균 목록
        stds (list): 표준편차 목록
        sizes (list, optional): 데이터 크기 목록. Defaults to [100, 100, 100].
        rounds (int, optional): 반올림 자리수. Defaults to 2.

    Returns:
        DataFrame: 정규분포를 따르는 데이터프레임
    """
    data = {}
    for i in range(0, len(means)):
        data[f"X{i+1}"] = my_normalize_data(means[i], stds[i], sizes[i], rounds)

    return DataFrame(data)


def my_pretty_table(data: DataFrame, headers: str = "keys") -> None:
    print(
        tabulate(
            data, headers="keys", tablefmt="psql", showindex=True, numalign="right"
        )
    )


def my_read_excel(
    path: str,
    sheet_name: str = None,
    index_col: str = None,
    timeindex: bool = False,
    info: bool = True,
    categories: list = None,
) -> DataFrame:
    """엑셀 파일을 데이터프레임으로 로드하고 정보를 출력한다.

    Args:
        path (str): 엑셀 파일의 경로(혹은 URL)
        sheet_name (str, optional): 엑셀파일에서 읽어들일 시트 이름
        index_col (str, optional): 인덱스 필드의 이름. Defaults to None.
        timeindex (bool, optional): True일 경우 인덱스를 시계열로 설정. Defaults to False.
        info (bool, optional): True일 경우 정보 출력. Defaults to True.
        categories (list, optional): 카테고리로 지정할 필드 목록. Defaults to None.

    Returns:
        DataFrame: 데이터프레임 객체
    """

    params = {}

    if sheet_name is not None:
        params["sheet_name"] = sheet_name

    if index_col is not None:
        params["index_col"] = index_col

    try:
        data: DataFrame = read_excel(path, **params)
    except Exception as e:
        raise Exception(f"\x1b[31m데이터를 로드하는데 실패했습니다. ({e})\x1b[0m")

    if timeindex:
        data.index = DatetimeIndex(data.index)

    if categories:
        data = my_category(data, *categories)

    if info:
        print(data.info())

    print("\n상위 5개 행")
    my_pretty_table(data.head())

    if info:
        print("\n하위 5개 행")
        my_pretty_table(data.tail())

        print("\n기술통계")
        desc = data.describe().T
        desc["nan"] = data.isnull().sum()
        my_pretty_table(desc)

        # 전달된 필드 이름 리스트가 있다면 반복
        if categories:
            print("\n카테고리 정보")
            for c in categories:
                d = DataFrame({"count": data[c].value_counts()})
                d.index.name = c
                my_pretty_table(d)

    return data


def my_standard_scaler(data: DataFrame, yname: str = None) -> DataFrame:
    """데이터프레임의 연속형 변수에 대해 Standard Scaling을 수행한다.

    Args:
        data (DataFrame): 데이터프레임 객체
        yname (str, optional): 종속변수의 컬럼명. Defaults to None.

    Returns:
        DataFrame: 표준화된 데이터프레임
    """
    # 원본 데이터 프레임 복사
    df = data.copy()

    # 종속변수만 별도로 분리
    if yname:
        y = df[yname]
        df = df.drop(yname, axis=1)

    # 카테고리 타입만 골라냄
    category_fields = []
    for f in df.columns:
        if df[f].dtypes not in ["int", "int32", "int64", "float", "float32", "float64"]:
            category_fields.append(f)

    cate = df[category_fields]
    df = df.drop(category_fields, axis=1)

    # 표준화 수행
    scaler = StandardScaler()
    std_df = DataFrame(scaler.fit_transform(df), index=data.index, columns=df.columns)

    # 분리했던 명목형 변수를 다시 결합
    if category_fields:
        std_df[category_fields] = cate

    # 분리했던 종속 변수를 다시 결합
    if yname:
        std_df[yname] = y

    return std_df


def my_minmax_scaler(data: DataFrame, yname: str = None) -> DataFrame:
    """데이터프레임의 연속형 변수에 대해 MinMax Scaling을 수행한다.

    Args:
        data (DataFrame): 데이터프레임 객체
        yname (str, optional): 종속변수의 컬럼명. Defaults to None.

    Returns:
        DataFrame: 표준화된 데이터프레임
    """
    # 원본 데이터 프레임 복사
    df = data.copy()

    # 종속변수만 별도로 분리
    if yname:
        y = df[yname]
        df = df.drop(yname, axis=1)

    # 카테고리 타입만 골라냄
    category_fields = []
    for f in df.columns:
        if df[f].dtypes not in ["int", "int32", "int64", "float", "float32", "float64"]:
            category_fields.append(f)

    cate = df[category_fields]
    df = df.drop(category_fields, axis=1)

    # 표준화 수행
    scaler = MinMaxScaler()
    std_df = DataFrame(scaler.fit_transform(df), index=data.index, columns=df.columns)

    # 분리했던 명목형 변수를 다시 결합
    if category_fields:
        std_df[category_fields] = cate

    # 분리했던 종속 변수를 다시 결합
    if yname:
        std_df[yname] = y

    return std_df


def my_train_test_split(
    data: DataFrame,
    yname: str = None,
    test_size: float = 0.2,
    random_state: int = get_random_state(),
    scalling: bool = False,
) -> tuple:
    """데이터프레임을 학습용 데이터와 테스트용 데이터로 나눈다.

    Args:
        data (DataFrame): 데이터프레임 객체
        yname (str, optional): 종속변수의 컬럼명. Defaults to None.
        test_size (float, optional): 검증 데이터의 비율(0~1). Defaults to 0.3.
        random_state (int, optional): 난수 시드. Defaults to 123.
        scalling (bool, optional): True일 경우 표준화를 수행한다. Defaults to False.

    Returns:
        tuple: x_train, x_test, y_train, y_test
    """
    if yname is not None:
        if yname not in data.columns:
            raise Exception(f"\x1b[31m종속변수 {yname}가 존재하지 않습니다.\x1b[0m")

        x = data.drop(yname, axis=1)
        y = data[yname]
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=test_size, random_state=random_state
        )

        if scalling:
            scaler = StandardScaler()
            x_train = DataFrame(
                scaler.fit_transform(x_train),
                index=x_train.index,
                columns=x_train.columns,
            )
            x_test = DataFrame(
                scaler.transform(x_test), index=x_test.index, columns=x_test.columns
            )

        return x_train, x_test, y_train, y_test
    else:
        train, test = train_test_split(
            data, test_size=test_size, random_state=random_state
        )

        if scalling:
            scaler = StandardScaler()
            train = DataFrame(
                scaler.fit_transform(train), index=train.index, columns=train.columns
            )
            test = DataFrame(
                scaler.transform(test), index=test.index, columns=test.columns
            )

        return train, test


def my_category(data: DataFrame, *args: str) -> DataFrame:
    """카테고리 데이터를 설정한다.

    Args:
        data (DataFrame): 데이터프레임 객체
        *args (str): 컬럼명 목록

    Returns:
        DataFrame: 카테고리 설정된 데이터프레임
    """
    df = data.copy()

    for k in args:
        df[k] = df[k].astype("category")

    return df


def my_unmelt(
    data: DataFrame, id_vars: str = "class", value_vars: str = "values"
) -> DataFrame:
    """두 개의 컬럼으로 구성된 데이터프레임에서 하나는 명목형, 나머지는 연속형일 경우
    명목형 변수의 값에 따라 고유한 변수를 갖는 데이터프레임으로 변환한다.

    Args:
        data (DataFrame): 데이터프레임
        id_vars (str, optional): 명목형 변수의 컬럼명. Defaults to 'class'.
        value_vars (str, optional): 연속형 변수의 컬럼명. Defaults to 'values'.

    Returns:
        DataFrame: 변환된 데이터프레임
    """
    result = data.groupby(id_vars)[value_vars].apply(list)
    mydict = {}

    for i in result.index:
        mydict[i] = result[i]

    return DataFrame(mydict)


def my_replace_missing_value(data: DataFrame, strategy: str = "mean") -> DataFrame:
    # 결측치 처리 규칙 생성
    imr = SimpleImputer(missing_values=np.nan, strategy=strategy)

    # 결측치 처리 규칙 적용 --> 2차원 배열로 반환됨
    df_imr = imr.fit_transform(data.values)

    # 2차원 배열을 데이터프레임으로 변환 후 리턴
    return DataFrame(df_imr, index=data.index, columns=data.columns)


def my_outlier_table(data: DataFrame, *fields: str):
    """데이터프레임의 사분위수와 결측치 경계값을 구한다.
    함수 호출 전 상자그림을 통해 결측치가 확인된 필드에 대해서만 처리하는 것이 좋다.

    Args:
        data (DataFrame): 데이터프레임
        *fields (str): 컬럼명 목록

    Returns:
        DataFrame: IQ
    """
    if not fields:
        fields = data.columns

    result = []
    for f in fields:
        # 숫자 타입이 아니라면 건너뜀
        if data[f].dtypes not in [
            "int",
            "int32",
            "int64",
            "float",
            "float32",
            "float64",
        ]:
            continue

        # 사분위수
        q1 = data[f].quantile(q=0.25)
        q2 = data[f].quantile(q=0.5)
        q3 = data[f].quantile(q=0.75)

        # 결측치 경계
        iqr = q3 - q1
        down = q1 - 1.5 * iqr
        up = q3 + 1.5 * iqr

        iq = {
            "FIELD": f,
            "Q1": q1,
            "Q2": q2,
            "Q3": q3,
            "IQR": iqr,
            "UP": up,
            "DOWN": down,
        }

        result.append(iq)

    return DataFrame(result).set_index("FIELD")


def my_replace_outliner(data: DataFrame, *fields: str) -> DataFrame:
    """이상치 경계값을 넘어가는 데이터를 경계값으로 대체한다.

    Args:
        data (DataFrame): 데이터프레임
        *fields (str): 컬럼명 목록

    Returns:
        DataFrame: 이상치가 경계값으로 대체된 데이터 프레임
    """

    # 원본 데이터 프레임 복사
    df = data.copy()

    # 카테고리 타입만 골라냄
    category_fields = []
    for f in df.columns:
        if df[f].dtypes not in ["int", "int32", "int64", "float", "float32", "float64"]:
            category_fields.append(f)

    cate = df[category_fields]
    df = df.drop(category_fields, axis=1)

    # 이상치 경계값을 구한다.
    outliner_table = my_outlier_table(df, *fields)

    # 이상치가 발견된 필드에 대해서만 처리
    for f in outliner_table.index:
        df.loc[df[f] < outliner_table.loc[f, "DOWN"], f] = outliner_table.loc[f, "DOWN"]
        df.loc[df[f] > outliner_table.loc[f, "UP"], f] = outliner_table.loc[f, "UP"]

    # 분리했던 카테고리 타입을 다시 병합
    if category_fields:
        df[category_fields] = cate

    return df


def my_replace_outliner_to_nan(data: DataFrame, *fields: str) -> DataFrame:
    """이상치를 결측치로 대체한다.

    Args:
        data (DataFrame): 데이터프레임
        *fields (str): 컬럼명 목록

    Returns:
        DataFrame: 이상치가 결측치로 대체된 데이터프레임
    """

    # 원본 데이터 프레임 복사
    df = data.copy()

    # 카테고리 타입만 골라냄
    category_fields = []
    for f in df.columns:
        if df[f].dtypes not in ["int", "int32", "int64", "float", "float32", "float64"]:
            category_fields.append(f)

    cate = df[category_fields]
    df = df.drop(category_fields, axis=1)

    # 이상치 경계값을 구한다.
    outliner_table = my_outlier_table(df, *fields)

    # 이상치가 발견된 필드에 대해서만 처리
    for f in outliner_table.index:
        df.loc[df[f] < outliner_table.loc[f, "DOWN"], f] = np.nan
        df.loc[df[f] > outliner_table.loc[f, "UP"], f] = np.nan

    # 분리했던 카테고리 타입을 다시 병합
    if category_fields:
        df[category_fields] = cate

    return df


def my_replace_outliner_to_mean(data: DataFrame, *fields: str) -> DataFrame:
    """이상치를 평균값으로 대체한다.

    Args:
        data (DataFrame): 데이터프레임
        *fields (str): 컬럼명 목록

    Returns:
        DataFrame: 이상치가 평균값으로 대체된 데이터프레임
    """
    # 원본 데이터 프레임 복사
    df = data.copy()

    # 카테고리 타입만 골라냄
    category_fields = []
    for f in df.columns:
        if df[f].dtypes not in ["int", "int32", "int64", "float", "float32", "float64"]:
            category_fields.append(f)

    cate = df[category_fields]
    df = df.drop(category_fields, axis=1)

    # 이상치를 결측치로 대체한다.
    if not fields:
        fields = df.columns

    df2 = my_replace_outliner_to_nan(df, *fields)

    # 결측치를 평균값으로 대체한다.
    df3 = my_replace_missing_value(df2, "mean")

    # 분리했던 카테고리 타입을 다시 병합
    if category_fields:
        df3[category_fields] = cate

    return df3


def my_drop_outliner(data: DataFrame, *fields: str) -> DataFrame:
    """이상치를 결측치로 변환한 후 모두 삭제한다.

    Args:
        data (DataFrame): 데이터프레임
        *fields (str): 컬럼명 목록

    Returns:
        DataFrame: 이상치가 삭제된 데이터프레임
    """

    df = my_replace_outliner_to_nan(data, *fields)
    return df.dropna()


def my_dummies(data: DataFrame, *args: str) -> DataFrame:
    """명목형 변수를 더미 변수로 변환한다.

    Args:
        data (DataFrame): 데이터프레임
        *args (str): 명목형 컬럼 목록

    Returns:
        DataFrame: 더미 변수로 변환된 데이터프레임
    """
    if not args:
        args = []

        for f in data.columns:
            if data[f].dtypes == "category":
                args.append(f)
    else:
        args = list(args)

    return get_dummies(data, columns=args, drop_first=True, dtype="int")


def my_trend(x: any, y: any, degree=2, value_count=100) -> tuple:
    """x, y 데이터에 대한 추세선을 구한다.

    Args:
        x (_type_): 산점도 그래프에 대한 x 데이터
        y (_type_): 산점도 그래프에 대한 y 데이터
        degree (int, optional): 추세선 방정식의 차수. Defaults to 2.
        value_count (int, optional): x 데이터의 범위 안에서 간격 수. Defaults to 100.

    Returns:
        tuple: (v_trend, t_trend)
    """
    # [ a, b, c ] ==> ax^2 + bx + c
    coeff = np.polyfit(x, y, degree)

    if type(x) == "list":
        minx = min(x)
        maxx = max(x)
    else:
        minx = x.min()
        maxx = x.max()

    v_trend = np.linspace(minx, maxx, value_count)

    t_trend = coeff[-1]
    for i in range(0, degree):
        t_trend += coeff[i] * v_trend ** (degree - i)

    return (v_trend, t_trend)


def my_poly_features(
    data: DataFrame, columns: any = None, ignore: any = None, degree: int = 2
) -> DataFrame:
    """전달된 데이터프레임에 대해서 2차항을 추가한 새로온 데이터프레임을 리턴한다.

    Args:
        data (DataFrame): 원본 데이터 프레임
        columns (any, optional): 2차항을 생성할 필드 목록. 전달되지 않을 경우 전체 필드에 대해 처리 Default to None.
        ignore (any, optional): 2차항을 생성하지 않을 필드 목록. Default to None.
        degree (int, optional): 차수. Default to 2

    Returns:
        DataFrame: 2차항이 추가된 새로운 데이터 프레임
    """
    df = data.copy()

    if not columns:
        columns = df.columns

    if not type(columns) == list:
        columns = [columns]

    ignore_df = None
    if ignore:
        if not type(ignore) == list:
            ignore = [ignore]

        ignore_df = df[ignore]
        df.drop(ignore, axis=1, inplace=True)

        columns = []
        for c in list(df.columns):
            if c not in ignore:
                columns.append(c)

    poly = PolynomialFeatures(degree=degree, include_bias=False)
    poly_fit = poly.fit_transform(df[columns])
    poly_df = DataFrame(poly_fit, columns=poly.get_feature_names_out(), index=df.index)

    df[poly_df.columns] = poly_df[poly_df.columns]

    if ignore_df is not None:
        df[ignore] = ignore_df

    return df


def my_labelling(data: DataFrame, *fields: str) -> DataFrame:
    """명목형 변수를 라벨링한다.

    Args:
        data (DataFrame): 데이터프레임
        *fields (str): 명목형 컬럼 목록

    Returns:
        DataFrame: 라벨링된 데이터프레임
    """
    df = data.copy()

    for f in fields:
        vc = sorted(list(df[f].unique()))
        label = {v: i for i, v in enumerate(vc)}
        df[f] = df[f].map(label).astype("int")

        # 라벨링 상황을 출력한다.
        i = []
        v = []
        for k in label:
            i.append(k)
            v.append(label[k])

        label_df = DataFrame({"label": v}, index=i)
        label_df.index.name = f
        my_pretty_table(label_df)

    return df


def my_balance(xdata: DataFrame, ydata: Series, method: str = "smote") -> DataFrame:
    """불균형 데이터를 균형 데이터로 변환한다.

    Args:
        xdata (DataFrame): 독립변수 데이터 프레임
        ydata (Series): 종속변수 데이터 시리즈
        method (str, optional): 균형화 방법 [smote, over, under]. Defaults to 'smote'.

    Returns:
        DataFrame: _description_
    """

    if method == "smote":
        smote = SMOTE(random_state=get_random_state())
        xdata, ydata = smote.fit_resample(xdata, ydata)
    elif method == "over":
        ros = RandomOverSampler(random_state=get_random_state())
        xdata, ydata = ros.fit_resample(xdata, ydata)
    elif method == "under":
        rus = RandomUnderSampler(random_state=get_random_state())
        xdata, ydata = rus.fit_resample(xdata, ydata)
    else:
        raise Exception(
            f"\x1b[31m지원하지 않는 방법입니다.(smote, over, under중 하나를 지정해야 합니다.) ({method})\x1b[0m"
        )

    return xdata, ydata


def my_vif_filter(
    data: DataFrame, yname: str = None, ignore: list = [], threshold: float = 10
) -> DataFrame:
    """독립변수 간 다중공선성을 검사하여 VIF가 threshold 이상인 변수를 제거한다.

    Args:
        data (DataFrame): 데이터프레임
        yname (str, optional): 종속변수 컬럼명. Defaults to None.
        ignore (list, optional): 제외할 컬럼 목록. Defaults to [].
        threshold (float, optional): VIF 임계값. Defaults to 10.

    Returns:
        DataFrame: VIF가 threshold 이하인 변수만 남은 데이터프레임
    """
    df = data.copy()

    if yname:
        y = df[yname]
        df = df.drop(yname, axis=1)

    # 카테고리 타입만 골라냄
    category_fields = []
    for f in df.columns:
        if df[f].dtypes not in ["int", "int32", "int64", "float", "float32", "float64"]:
            category_fields.append(f)

    cate = df[category_fields]
    df = df.drop(category_fields, axis=1)

    # 제외할 필드를 제거
    if ignore:
        ignore_df = df[ignore]
        df = df.drop(ignore, axis=1)

    # VIF 계산
    while True:
        xnames = list(df.columns)
        vif = {}

        for x in xnames:
            vif[x] = variance_inflation_factor(df, xnames.index(x))

        maxkey = max(vif, key=vif.get)

        if vif[maxkey] <= threshold:
            break

        df = df.drop(maxkey, axis=1)

    # 분리했던 명목형 변수를 다시 결합
    if category_fields:
        df[category_fields] = cate

    # 분리했던 제외할 필드를 다시 결합
    if ignore:
        df[ignore] = ignore_df

    # 분리했던 종속 변수를 다시 결합
    if yname:
        df[yname] = y

    return df


def my_pca(
    data: DataFrame,
    n_components: int | float = 0.95,
    standardize: bool = True,
    plot: bool = True,
    figsize: tuple = (15, 7),
    dpi: int = 100,
) -> DataFrame:
    """PCA를 수행하여 차원을 축소한다.

    Args:
        data (DataFrame): 데이터프레임
        n_components (int, optional): 축소할 차원 수. Defaults to 2.
        standardize (bool, optional): True일 경우 표준화를 수행한다. Defaults to False.

    Returns:
        DataFrame: PCA를 수행한 데이터프레임
    """
    if standardize:
        df = my_standard_scaler(data)
    else:
        df = data.copy()

    model = pca(n_components=n_components, random_state=get_random_state())
    result = model.fit_transform(X=df)

    my_pretty_table(result["loadings"])
    my_pretty_table(result["topfeat"])

    if plot:
        fig, ax = model.biplot(figsize=figsize, fontsize=12, dpi=dpi)
        ax.set_title(ax.get_title(), fontsize=14)
        ax.set_xlabel(ax.get_xlabel(), fontsize=12)
        ax.set_ylabel(ax.get_ylabel(), fontsize=12)
        ax.set_xticklabels(ax.get_xticklabels(), fontsize=11)
        ax.set_yticklabels(ax.get_yticklabels(), fontsize=11)
        plt.show()
        plt.close()

        fig, ax = model.plot(figsize=figsize)
        fig.set_dpi(dpi)
        ax.set_title(ax.get_title(), fontsize=14)
        ax.set_xlabel(ax.get_xlabel(), fontsize=12)
        ax.set_ylabel(ax.get_ylabel(), fontsize=12)

        labels = ax.get_xticklabels()
        pc_labels = [f"PC{i+1}" for i in range(len(labels))]
        ax.set_xticklabels(pc_labels, fontsize=11, rotation=0)

        ax.set_yticklabels(ax.get_yticklabels(), fontsize=11)
        plt.show()
        plt.close()

        plt.rcParams["font.family"] = (
            "AppleGothic" if sys.platform == "darwin" else "Malgun Gothic"
        )

    return result["PC"]
