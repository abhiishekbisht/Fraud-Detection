from pydantic import BaseModel, Field, ConfigDict

class TransactionFeatures(BaseModel):
    Time: float = Field(..., description="Number of seconds elapsed between this transaction and the first transaction in the dataset.")
    Amount: float = Field(..., description="Transaction amount.")
    V1: float = Field(..., description="Anonymized PCA feature V1.")
    V2: float = Field(..., description="Anonymized PCA feature V2.")
    V3: float = Field(..., description="Anonymized PCA feature V3.")
    V4: float = Field(..., description="Anonymized PCA feature V4.")
    V5: float = Field(..., description="Anonymized PCA feature V5.")
    V6: float = Field(..., description="Anonymized PCA feature V6.")
    V7: float = Field(..., description="Anonymized PCA feature V7.")
    V8: float = Field(..., description="Anonymized PCA feature V8.")
    V9: float = Field(..., description="Anonymized PCA feature V9.")
    V10: float = Field(..., description="Anonymized PCA feature V10.")
    V11: float = Field(..., description="Anonymized PCA feature V11.")
    V12: float = Field(..., description="Anonymized PCA feature V12.")
    V13: float = Field(..., description="Anonymized PCA feature V13.")
    V14: float = Field(..., description="Anonymized PCA feature V14.")
    V15: float = Field(..., description="Anonymized PCA feature V15.")
    V16: float = Field(..., description="Anonymized PCA feature V16.")
    V17: float = Field(..., description="Anonymized PCA feature V17.")
    V18: float = Field(..., description="Anonymized PCA feature V18.")
    V19: float = Field(..., description="Anonymized PCA feature V19.")
    V20: float = Field(..., description="Anonymized PCA feature V20.")
    V21: float = Field(..., description="Anonymized PCA feature V21.")
    V22: float = Field(..., description="Anonymized PCA feature V22.")
    V23: float = Field(..., description="Anonymized PCA feature V23.")
    V24: float = Field(..., description="Anonymized PCA feature V24.")
    V25: float = Field(..., description="Anonymized PCA feature V25.")
    V26: float = Field(..., description="Anonymized PCA feature V26.")
    V27: float = Field(..., description="Anonymized PCA feature V27.")
    V28: float = Field(..., description="Anonymized PCA feature V28.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "Time": 0.0,
                "Amount": 125.50,
                "V1": -1.358354, "V2": -1.340163, "V3": 1.773209, "V4": 0.379780,
                "V5": -0.503198, "V6": 1.800499, "V7": 0.791461, "V8": 0.247676,
                "V9": -1.514654, "V10": 0.207643, "V11": 0.624501, "V12": 0.066084,
                "V13": 0.717293, "V14": -0.165946, "V15": 2.345865, "V16": -2.890083,
                "V17": 1.109969, "V18": -0.121359, "V19": -2.261857, "V20": 0.524980,
                "V21": 0.247998, "V22": 0.771679, "V23": 0.909412, "V24": -0.689281,
                "V25": -0.327642, "V26": -0.139097, "V27": -0.055353, "V28": -0.059752
            }
        }
    )
