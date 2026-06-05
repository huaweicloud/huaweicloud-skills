# Phase 2: Data CopyOptimization — DetailedReference

## 2.1 Single Transfer Size >= 16 KB

Bandwidth UtilizationfollowSingle Transfer Sizeincreaselargeandliftupgrade. actualtestExperience: SingleData Copy **>= 16 KB** time, 
UB↔HBM twocountmethoddirectionaveragecanreachtoconnectnearpeakvalueofbandwidthwidth. lowinthisvaluetimeBandwidth Utilizationdisplayfamousunderdowngrade. 

setcalculate Tiling strategystrategytimeshouldconfirmkeepeachtime `DataCopy` Data Copyarrivefew 16 KB. 

## 2.2 GM regionaddress 512B pairalign

in Atlas A2 trainpracticesystemcolumn / Atlas 800I A2 pushmanageproduceproductabove, GM regionaddress 512B pairaligncancompare 32B
pairalignobtainobtainmosthigh **30%** ofbandwidthwidthliftupgrade (mostdifferenceScenariosunderofdifferencedistance) . 

distributematch GM Tensor orCalculationpartialmoveamounttime, shouldconfirmkeeprisebegincharactersectionregionaddressas 512 ofadjustnumbertimes. 

## 2.3 Usage stride parameternumberrepresentsubstitute for loopring

Usage `DataCopyParams` (blockCount / blockLen / srcStride / dstStride) willbetweenseparate
Data CopyDescriptionasoneitem DMA fingercommandunderissue, andnonuse for loopringIterativetraveladjustuse `DataCopy`. 

**reverseexample** — for loopring, eachtimeonlyData Copy 2 KB: 

```cpp
constexpr int32_t copyWidth = 2 * 1024 / sizeof(float);
constexpr int32_t imgWidth  = 16 * 1024 / sizeof(float);
constexpr int32_t imgHeight = 16;
// 16 timealoneestablishof 2KB Data Copy, Bandwidth Utilizationextremelow
for (int i = 0; i < imgHeight; i++) {
    DataCopy(tensorIn[i * copyWidth], tensorGM[i * imgWidth], copyWidth);
}
```

**positiveexample** — singleitem DMA Descriptioncharacter, onetimeData Copy 32 KB: 

```cpp
constexpr int32_t copyWidth = 2 * 1024 / sizeof(float);
constexpr int32_t imgWidth  = 16 * 1024 / sizeof(float);
constexpr int32_t imgHeight = 16;
DataCopyParams copyParams;
copyParams.blockCount = imgHeight;                     // 16 travel
copyParams.blockLen   = copyWidth / 8;                 // singlebit: 32B DataBlock
copyParams.srcStride  = (imgWidth - copyWidth) / 8;    // src travelbetweenbetweenseparate
copyParams.dstStride  = 0;                             // dst connectcontinuecomposeinput
DataCopy(tensorGM, tensorIn, copyParams);
```

stride methodsunderissueoneitem DMA fingercommand, HardwareselfmaincompletedallpartData Copy, canfilldistributeutilizeusebandwidthwidth. 
for loopringmethodsunderissue 16 itemsmall DMA fingercommand, eachitemofbetweenalsohave Scalar openconsume. 
