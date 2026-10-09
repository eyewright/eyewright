# Calibration for gemma4:12b
fit=1200  holdout=600  test=600   platt a=0.182 b=0.143
split      raw ECE/Brier        isotonic             platt               
fit        (0.13, 0.1591)       (0.1742, 0.1831)     (0.1208, 0.1615)    
holdout    (0.124, 0.1525)      (0.1591, 0.1657)     (0.1108, 0.1565)    
test       (0.132, 0.1615)      (0.1766, 0.1833)     (0.1167, 0.1618)    

wrote responses-train-gemma12b-cal.jsonl and responses-gemma12b-cal.jsonl
# Calibration for jev-router
fit=1196  holdout=599  test=598   platt a=0.827 b=-0.507
split      raw ECE/Brier        isotonic             platt               
fit        (0.0642, 0.1393)     (0.0525, 0.1489)     (0.0296, 0.1308)    
holdout    (0.0604, 0.1294)     (0.0401, 0.1322)     (0.0381, 0.119)     
test       (0.0703, 0.1353)     (0.0465, 0.1306)     (0.0406, 0.1228)    

wrote responses-train-jev-router-cal.jsonl and responses-jev-router-cal.jsonl
# Calibration for jev-1.13
fit=1200  holdout=600  test=600   platt a=1.378 b=0.077
split      raw ECE/Brier        isotonic             platt               
fit        (0.0568, 0.1526)     (0.0114, 0.1455)     (0.0333, 0.1497)    
holdout    (0.0754, 0.1463)     (0.0255, 0.1391)     (0.0419, 0.1439)    
test       (0.0805, 0.139)      (0.0473, 0.1293)     (0.057, 0.1333)     

wrote responses-train-jev-113-cal.jsonl and responses-jev-113-cal.jsonl
