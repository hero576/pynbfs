## 简介

用于解析.NET中使用NBFS协议编码的二进制数据。使用的是[koutto](https://github.com/koutto/dotnet-binary-deserializer)的库，修改了其中的bug。

## 安装

```
pip install NBFS
```

## 使用

### 二进制解码为XML

```python
from NBFS import NBFS

print(NBFS.bin2xml(b'\x40\x03\x44\x4F\x43'))

# output: <DOC ></DOC>
```

### XML转换为二进制文件 - 格式[MC-NBFS]

```python
from NBFS import NBFS

print(NBFS.xml2bin('<DOC></DOC>')) # 同样可以使用xml2mcnbfs方法

# output: b'@\x03DOC\x01'
```


### XML转换为二进制文件 - 格式[MC-NBFSE]

```python
from NBFS import NBFS

print(NBFS.xml2mcnbfse('<DOC></DOC>'))

# output: bytearray(b'@\x03DOC\x01')
```
