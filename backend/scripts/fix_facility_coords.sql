-- ============================================================
-- 修正 facilities 表坐标：所有地址通过高德 geocoding API 获取真实坐标
-- 生成时间: 2026-06-23 08:52:57
-- 用法: 直接在 MySQL 中执行此脚本
-- ============================================================

START TRANSACTION;

-- 芙蓉区五一大道80号 (坐标无变化，跳过)
-- 芙蓉区芙蓉中路一段168号 (坐标无变化，跳过)
-- 芙蓉区解放西路18号 (坐标无变化，跳过)
-- [天心区] 天心区韶山南路123号  旧:(28.114500, 112.996900) → 新:(28.143245, 112.995514)  偏移约 3194m
UPDATE facilities SET location_lng = 112.995514, location_lat = 28.143245 WHERE address = '天心区韶山南路123号' AND district = '天心区';

-- [天心区] 天心区书院南路306号  旧:(28.108500, 112.985000) → 新:(28.150078, 112.973137)  偏移约 4799m
UPDATE facilities SET location_lng = 112.973137, location_lat = 28.150078 WHERE address = '天心区书院南路306号' AND district = '天心区';

-- [天心区] 天心区劳动西路289号  旧:(28.121500, 112.991000) → 新:(28.175935, 112.980662)  偏移约 6150m
UPDATE facilities SET location_lng = 112.980662, location_lat = 28.175935 WHERE address = '天心区劳动西路289号' AND district = '天心区';

-- [岳麓区] 岳麓区岳麓大道142号  旧:(28.234202, 112.930116) → 新:(28.227054, 112.947410)  偏移约 2077m
UPDATE facilities SET location_lng = 112.94741, location_lat = 28.227054 WHERE address = '岳麓区岳麓大道142号' AND district = '岳麓区';

-- [岳麓区] 岳麓区麓山南路932号  旧:(28.187549, 112.936763) → 新:(28.168544, 112.930610)  偏移约 2217m
UPDATE facilities SET location_lng = 112.93061, location_lat = 28.168544 WHERE address = '岳麓区麓山南路932号' AND district = '岳麓区';

-- [岳麓区] 岳麓区枫林三路1099号  旧:(28.192840, 112.902673) → 新:(28.198770, 112.861673)  偏移约 4598m
UPDATE facilities SET location_lng = 112.861673, location_lat = 28.19877 WHERE address = '岳麓区枫林三路1099号' AND district = '岳麓区';

-- [开福区] 开福区三一大道66号  旧:(28.251500, 112.991000) → 新:(28.228936, 112.991962)  偏移约 2507m
UPDATE facilities SET location_lng = 112.991962, location_lat = 28.228936 WHERE address = '开福区三一大道66号' AND district = '开福区';

-- [开福区] 开福区芙蓉北路二段200号  旧:(28.256500, 112.986000) → 新:(28.229685, 112.988067)  偏移约 2985m
UPDATE facilities SET location_lng = 112.988067, location_lat = 28.229685 WHERE address = '开福区芙蓉北路二段200号' AND district = '开福区';

-- [开福区] 开福区湘江北路1500号  旧:(28.261500, 112.979000) → 新:(28.238718, 112.978925)  偏移约 2529m
UPDATE facilities SET location_lng = 112.978925, location_lat = 28.238718 WHERE address = '开福区湘江北路1500号' AND district = '开福区';

-- [雨花区] 雨花区长沙大道598号  旧:(28.135400, 113.041600) → 新:(28.167394, 113.046100)  偏移约 3586m
UPDATE facilities SET location_lng = 113.0461, location_lat = 28.167394 WHERE address = '雨花区长沙大道598号' AND district = '雨花区';

-- [雨花区] 雨花区韶山南路633号  旧:(28.130400, 113.043600) → 新:(28.129291, 113.004837)  偏移约 4304m
UPDATE facilities SET location_lng = 113.004837, location_lat = 28.129291 WHERE address = '雨花区韶山南路633号' AND district = '雨花区';

-- [雨花区] 雨花区香樟路819号  旧:(28.140400, 113.039600) → 新:(28.137697, 113.032703)  偏移约 822m
UPDATE facilities SET location_lng = 113.032703, location_lat = 28.137697 WHERE address = '雨花区香樟路819号' AND district = '雨花区';

-- [望城区] 望城区雷锋大道999号  旧:(28.361400, 112.830700) → 新:(28.281533, 112.875936)  偏移约 10188m
UPDATE facilities SET location_lng = 112.875936, location_lat = 28.281533 WHERE address = '望城区雷锋大道999号' AND district = '望城区';

-- [望城区] 望城区金星北路四段89号  旧:(28.366400, 112.835700) → 新:(28.314245, 112.890015)  偏移约 8358m
UPDATE facilities SET location_lng = 112.890015, location_lat = 28.314245 WHERE address = '望城区金星北路四段89号' AND district = '望城区';

-- [望城区] 望城区望城大道100号  旧:(28.356400, 112.825700) → 新:(28.339665, 112.828461)  偏移约 1883m
UPDATE facilities SET location_lng = 112.828461, location_lat = 28.339665 WHERE address = '望城区望城大道100号' AND district = '望城区';

-- [长沙县] 长沙县星沙大道188号  旧:(28.246900, 113.080200) → 新:(28.250066, 113.087990)  偏移约 933m
UPDATE facilities SET location_lng = 113.08799, location_lat = 28.250066 WHERE address = '长沙县星沙大道188号' AND district = '长沙县';

-- [长沙县] 长沙县开元中路45号  旧:(28.251900, 113.085200) → 新:(28.246723, 113.085175)  偏移约 575m
UPDATE facilities SET location_lng = 113.085175, location_lat = 28.246723 WHERE address = '长沙县开元中路45号' AND district = '长沙县';

-- [长沙县] 长沙县板仓路200号  旧:(28.241900, 113.075200) → 新:(28.241654, 113.078354)  偏移约 351m
UPDATE facilities SET location_lng = 113.078354, location_lat = 28.241654 WHERE address = '长沙县板仓路200号' AND district = '长沙县';

-- [浏阳市] 浏阳市浏阳大道11号  旧:(28.163900, 113.643200) → 新:(28.155944, 113.632985)  偏移约 1437m
UPDATE facilities SET location_lng = 113.632985, location_lat = 28.155944 WHERE address = '浏阳市浏阳大道11号' AND district = '浏阳市';

-- [浏阳市] 浏阳市花炮大道88号  旧:(28.168900, 113.648200) → 新:(28.162385, 113.606397)  偏移约 4696m
UPDATE facilities SET location_lng = 113.606397, location_lat = 28.162385 WHERE address = '浏阳市花炮大道88号' AND district = '浏阳市';

-- [浏阳市] 浏阳市金沙中路100号  旧:(28.158900, 113.638200) → 新:(28.136992, 113.627456)  偏移约 2708m
UPDATE facilities SET location_lng = 113.627456, location_lat = 28.136992 WHERE address = '浏阳市金沙中路100号' AND district = '浏阳市';

-- [宁乡市] 宁乡市金洲大道宁乡段  旧:(28.277400, 112.553800) → 新:(28.273499, 112.556661)  偏移约 537m
UPDATE facilities SET location_lng = 112.556661, location_lat = 28.273499 WHERE address = '宁乡市金洲大道宁乡段' AND district = '宁乡市';

-- [宁乡市] 宁乡市玉潭中路50号  旧:(28.282400, 112.558800) → 新:(28.253184, 112.561509)  偏移约 3257m
UPDATE facilities SET location_lng = 112.561509, location_lat = 28.253184 WHERE address = '宁乡市玉潭中路50号' AND district = '宁乡市';

-- [宁乡市] 宁乡市一环北路20号  旧:(28.272400, 112.548800) → 新:(28.258680, 112.543838)  偏移约 1619m
UPDATE facilities SET location_lng = 112.543838, location_lat = 28.25868 WHERE address = '宁乡市一环北路20号' AND district = '宁乡市';

-- 变更: 24 条, 无变化: 3 条, 共 27 条
COMMIT;
-- ROLLBACK;  -- 如需回滚，取消此行注释并注释 COMMIT
