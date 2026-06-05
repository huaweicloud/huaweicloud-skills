## msprofguideoutputdbformatformulaDataDescription

msprofcommandcommandExecution Completeafter, ableGenerate aSummaryallhavePerformanceDataofmsprof\_\{timebetweenstab\}.dbtableStructurefile, oughtfilepushrecommendUsageMindStudio InsightToolssearchsee, alsocanin order toUsageNavicat PremiumetcDatabaseDevelopmentToolsstraightconnectprintopen. whenpreviousdbfileSummaryofPerformanceDataifunder: 

>[!NOTE] Description 
>dbfileaveragein order totableformatshapeformulaexpandshowPerformanceData, andallhaveDataaveragein order tonumbercharacterreflectshoot (exampleifopNamecharacterparagraphunderofOperatornamedisplayshowas194) , numbercharacterandNameofreflectshoottableas[STRING\_IDS](#zh-cn_topic_0000002076410600_section116561584178). 

**singlebitRelated**

1. timebetweenRelated, statisticsoneUsagecontainsecond (ns) , andasthisregionUnixtimebetween. 
2. MemoryRelated, statisticsoneUsagecharactersection (Byte) . 
3. bandwidthwidthRelated, statisticsoneUsageByte/s. 
4. frequencyrateRelated, statisticsoneUsageMHz. 

**ENUM\_API\_TYPE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 1**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, ID|
|name|TEXT|APItypetype|

**table 2**  insidecontent

|id|name|
|--|--|
|20000|acl|
|15000|model|
|10000|node|
|5500|communication|
|5000|runtime|
|50001|op|
|50002|queue|
|50003|trace|
|50004|mstx|

**ENUM\_MODULE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 3**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, ID|
|name|TEXT|Componentsname|

**table 4**  insidecontent

|id|name|
|--|--|
|0|SLOG|
|1|IDEDD|
|2|SCC|
|3|HCCL|
|4|FMK|
|5|CCU|
|6|DVPP|
|7|RUNTIME|
|8|CCE|
|9|HDC|
|10|DRV|
|11|NET|
|22|DEVMM|
|23|KERNEL|
|24|LIBMEDIA|
|25|CCECPU|
|27|ROS|
|28|HCCP|
|29|ROCE|
|30|TEFUSION|
|31|PROFILING|
|32|DP|
|33|APP|
|34|TS|
|35|TSDUMP|
|36|AICPU|
|37|LP|
|38|TDT|
|39|FE|
|40|MD|
|41|MB|
|42|ME|
|43|IMU|
|44|IMP|
|45|GE|
|47|CAMERA|
|48|ASCENDCL|
|49|TEEOS|
|50|ISP|
|51|SIS|
|52|HSM|
|53|DSS|
|54|PROCMGR|
|55|BBOX|
|56|AIVECTOR|
|57|TBE|
|58|FV|
|59|MDCMAP|
|60|TUNE|
|61|HSS|
|62|FFTS|
|63|OP|
|64|UDF|
|65|HICAID|
|66|TSYNC|
|67|AUDIO|
|68|TPRT|
|69|ASCENDCKERNEL|
|70|ASYS|
|71|ATRACE|
|72|RTC|
|73|SYSMONITOR|
|74|AMP|
|75|ADETECT|
|76|MBUFF|
|77|CUSTOM|

**ENUM\_HCCL\_DATA\_TYPE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 5**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, ID|
|name|TEXT|throughinformationDatatypetype|

**table 6**  insidecontent

|id|name|
|--|--|
|0|INT8|
|1|INT16|
|2|INT32|
|3|FP16|
|4|FP32|
|5|INT64|
|6|UINT64|
|7|UINT8|
|8|UINT16|
|9|UINT32|
|10|FP64|
|11|BFP16|
|12|INT128|
|255|RESERVED|
|65534|N/A|
|65535|INVALID_TYPE|

**ENUM\_HCCL\_LINK\_TYPE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 7**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, ID|
|name|TEXT|throughinformationlinkpathtypetype|

**table 8**  insidecontent

|id|name|
|--|--|
|0|ON_CHIP|
|1|HCCS|
|2|PCIE|
|3|ROCE|
|4|SIO|
|5|HCCS_SW|
|6|STANDARD_ROCE|
|255|RESERVED|
|65534|N/A|
|65535|INVALID_TYPE|

**ENUM\_HCCL\_TRANSPORT\_TYPE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 9**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, ID|
|name|TEXT|throughinformationtransferoutputtypetype|

**table 10**  insidecontent

|id|name|
|--|--|
|0|SDMA|
|1|RDMA|
|2|LOCAL|
|255|RESERVED|
|65534|N/A|
|65535|INVALID_TYPE|

**ENUM\_HCCL\_RDMA\_TYPE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 11**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, ID|
|name|TEXT|throughinformationRDMAtypetype|

**table 12**  insidecontent

|id|name|
|--|--|
|0|RDMA_SEND_NOTIFY|
|1|RDMA_SEND_PAYLOAD|
|255|RESERVED|
|65534|N/A|
|65535|INVALID_TYPE|

**ENUM\_MSTX\_EVENT\_TYPE**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 13**  formatformula

|characterparagraphname| typetype     |containmeaning|
|--|--------|--|
|id| INTEGER |searchlead, HostsidetxprintpointDataeventtypetypeCorrespondingofID|
|name| TEXT   |HostsidetxprintpointDataeventtypetype|

**table 14**  insidecontent

|id|name|
|--|--|
|0|marker|
|1|push/pop|
|2|start/end|
|3|marker_ex|

**ENUM\_MEMCPY\_OPERATION**

pieceraisetable. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 15**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|mainkey, ID|
|name|TEXT|copyshelltypetype|

**table 16**  insidecontent

|id|name|
|--|--|
|0|host to host|
|1|host to device|
|2|device to host|
|3|device to device|
|4|managed memory|
|5|addr device to device|
|6|host to device ex|
|7|device to host ex|
|65535|other|

**STRING\_IDS**

reflectshoottable, Used forMemoryIDandcharactercharacterstringreflectshootrelatedsystem. 

noCorrespondingopenrelated. 

**table 17**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|searchlead, string ID|
|value|TEXT|string value|

**SESSION\_TIME\_INFO**

timebetweentable, Used forMemoryPerformanceDatamiddleofopenbeginconclusionendtimebetween. inCollectionnotpositiveoftenretreatoutputtime, noconclusionendtimebetween. 

noCorrespondingopenrelated. 

**table 18**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|startTimeNs|INTEGER|TaskopenstarttimeofUnixtimebetween, singlebitns|
|endTimeNs|INTEGER|TaskconclusionendtimeofUnixtimebetween, singlebitns|

**NPU\_INFO**

CorrespondingdeviceIdofcoreslicetypesign. 

noCorrespondingopenrelated. 

**table 19**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|id|INTEGER|DeviceID, displayshowas-1timetableshownotCollectiontodeviceId|
|name|TEXT|DeviceCorrespondingofcoreslicetypesign|

**HOST\_INFO**

hostUidandName. 

noCorrespondingopenrelated. 

**table 20**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|hostUid|TEXT|standardrecognizeHostofonlyoneID|
|hostName|TEXT|HostmainmachineName, iflocalhost|

**TASK**

taskData, presentappearallhaveHardwareExecuteofOperatorinformationinformation. 

by--task-timeopenrelatedControl. 

**table 21**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|startNs|INTEGER|andglobalTaskIdconnectmatchsearchlead, searchleadNameTaskIndex, OperatorTaskopenbegintimebetween, singlebitns|
|endNs|INTEGER|OperatorTaskconclusionendtimebetween, singlebitns|
|deviceId|INTEGER|OperatorTaskCorrespondingofDeviceID|
|connectionId|INTEGER|Generatehost-deviceconnectline|
|globalTaskId|INTEGER|andstartNsconnectmatchsearchlead, searchleadNameTaskIndex, Used foronlyonestandardrecognizeGlobalOperatorTask|
|globalPid|INTEGER|OperatorTaskExecutetimeofPID|
|taskType|INTEGER|DeviceExecuteoughtOperatorofaddspeedadaptertypetype|
|contextId|INTEGER|Used forregiondistributechildfiguresmallOperator, oftenseeinMIXOperatorandFFTS+Task|
|streamId|INTEGER|OperatorTaskCorrespondingofstreamId|
|taskId|INTEGER|OperatorTaskCorrespondingoftaskId|
|modelId|INTEGER|OperatorTaskCorrespondingofmodelId|

**COMPUTE\_TASK\_INFO**

CalculationOperatorDescriptioninformationinformation. 

by--task-timeopenrelatedControl. 

**table 22**  formatformula

| characterparagraphname             |typetype|containmeaning|
|-----------------|--|--|
| name            |INTEGER|Operatorname, STRING_IDS(name)|
| globalTaskId    |INTEGER|searchlead, GlobalOperatorTaskID, Used forrelatedconnectTASKtable|
| blockDim        |INTEGER|OperatorRunTilingnumberamount, CorrespondingOperatorRuntimeCore count|
| mixBlockDim     |INTEGER|mixOperatorfromaddspeedadapterofBlockNumvalue|
| taskType        |INTEGER|HostExecuteoughtOperatorofaddspeedadaptertypetype, STRING_IDS(taskType)|
| opType          |INTEGER|Operatortypetype, STRING_IDS(opType)|
| inputFormats    |INTEGER|OperatoroutputinputDataformatformula, STRING_IDS(inputFormats)|
| inputDataTypes  |INTEGER|OperatoroutputinputDatatypetype, STRING_IDS(inputDataTypes)|
| inputShapes     |INTEGER|Operatorofoutputinputdimensiondegree, STRING_IDS(inputShapes)|
| outputFormats   |INTEGER|OperatorOutputDataformatformula, STRING_IDS(outputFormats)|
| outputDataTypes |INTEGER|OperatorOutputDatatypetype, STRING_IDS(outputDataTypes)|
| outputShapes    |INTEGER|OperatorOutputdimensiondegree, STRING_IDS(outputShapes)|
| attrInfo        |INTEGER|Operatorofattrinformationinformation, usecomereflectshootOperatorshape, OperatorCustomofparameternumberetc, STRING_IDS(attrInfo)|
| opState         |INTEGER|Operatorofmovequietstateinformationinformation, dynamictableshowmovestateOperator, statictableshowquietstateOperator, N/AtableshowoughtScenariosoroughtOperatornotrecognizecategory, STRING_IDS(opState)|
| hf32Eligible    |INTEGER|standardrecognizeiswhetherUsageHF32precisiondegreestandardremember, YEStableshowUsage, NOtableshownotUsage, N/AtableshowoughtScenariosoroughtOperatornotrecognizecategory, STRING_IDS(hf32Eligible)|

**COMMUNICATION\_TASK\_INFO**

DescriptionthroughinformationsmallOperatorinformationinformation. 

by--task-time, --hccl, --ascendclopenrelatedControlCorrespondingDataofCollection. Configuration--task-timeasnonl0timeDatahavevalid. havethroughinformationDataofScenariosundersilentrecognizeGenerateoughttable. 

**table 23**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|name|INTEGER|Operatorname, STRING_IDS(name)|
|globalTaskId|INTEGER|searchlead, searchleadNameCommunicationTaskIndex, GlobalOperatorTaskID, Used forrelatedconnectTASKtable|
|taskType|INTEGER|Operatortypetype, STRING_IDS(taskType)|
|planeId|INTEGER|networknetworkaveragesurfaceID|
|groupName|INTEGER|throughinformationdomain, STRING_IDS(groupName)|
|notifyId|INTEGER|notifyonlyoneID|
|rdmaType|INTEGER|RDMAtypetype, Packagecontain: RDMASendNotify, RDMASendPayload, ENUM_HCCL_RDMA_TYPE(rdmaType)|
|srcRank|INTEGER|sourceRank|
|dstRank|INTEGER|itemofRank|
|transportType|INTEGER|transferoutputtypetype, Packagecontain: LOCAL, SDMA, RDMA, ENUM_HCCL_TRANSPORT_TYPE(transportType)|
|size|INTEGER|Dataamount, singlebitByte|
|dataType|INTEGER|Dataformatformula, ENUM_HCCL_DATA_TYPE(dataType)|
|linkType|INTEGER|linkpathtypetype, Packagecontain: HCCS, PCIe, RoCE, ENUM_HCCL_LINK_TYPE(linkType)|
|opId|INTEGER|CorrespondingoflargeOperatorId, Used forrelatedconnectCOMMUNICATION_OPtable|
|isMaster|INTEGER|standardremembermainfromflowthroughinformationOperator, Analysistimein order tomainflowOperatorasstandard, getvalueas: 0: fromflow1: mainflow|
|bandwidth|NUMERIC|oughtthroughinformationsmallOperatorofbandwidthwidthData, singlebitByte / s|

**COMMUNICATION\_OP**

DescriptionthroughinformationlargeOperatorinformationinformation. 

by--task-time, --hcclopenrelatedControlCorrespondingDataofCollection. havethroughinformationDataofScenariosundersilentrecognizeGenerateoughttable. 

**table 24**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|opName|INTEGER|Operatorname, STRING_IDS(opName), example: hcom_allReduce__428_0_1|
|startNs|INTEGER|throughinformationlargeOperatorofopenbegintimebetween, singlebitns|
|endNs|INTEGER|throughinformationlargeOperatorofconclusionendtimebetween, singlebitns|
|connectionId|INTEGER|Generatehost-deviceconnectline|
|groupName|INTEGER|throughinformationdomain, STRING_IDS(groupName), example: 10.170.22.98%enp67s0f5_60000_0_1708156014257149|
|opId|INTEGER|searchlead, throughinformationlargeOperatorId, Used forrelatedconnectCOMMUNICATION_TASK_INFOtable|
|relay|INTEGER|leasetrackthroughinformationstandardrecognize|
|retry|INTEGER|weighttransferstandardrecognize|
|dataType|INTEGER|largeOperatortransferoutputofDatatypetype, if (INT8, FP32) , ENUM_HCCL_DATA_TYPE(dataType)|
|algType|INTEGER|throughinformationOperatorUsageofcomputemethod, candistributeasmultiplecountPhase, STRING_IDS(algType), if (HD-MESH) |
|count|NUMERIC|OperatortransferoutputofdataTypetypetypeofDataamount|
|opType|INTEGER|Operatortypetype, STRING_IDS(opType), example: hcom_broadcast_|
|deviceld|INTEGER|DeviceID|

**CANN\_API**

CANN APIData. 

by--ascendclopenrelatedControl. 

**table 25**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|startNs|INTEGER|APIofopenbegintimebetween, singlebitns|
|endNs|INTEGER|APIofconclusionendtimebetween, singlebitns|
|type|INTEGER|APItypetype, ENUM_API_TYPE(type)|
|globalTid|INTEGER|APIallattributeofGlobalTID. high32bit: PID, low32bit: TID|
|connectionId|INTEGER|searchlead, Used forrelatedconnectTASKtableandCOMMUNICATION_OPtable|
|name|INTEGER|APIofName, STRING_IDS(name)|

**QOS**

keepkeepQoSofData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 26**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|eventName|NUMERIC|QoSmatterfileName, STRING_IDS(eventName)|
|bandwidth|NUMERIC|QoSCorrespondingtimebetweenofbandwidthwidth, singlebitByte / s|
|timestampNs|NUMERIC|thisregiontimebetween, singlebitns|

**AICORE\_FREQ**

AI Corefrequencyrateinformationinformation. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 27**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceld|INTEGER|DeviceID|
|timestampNs|NUMERIC|frequencyratechangetransformtimeofthisregiontimebetween, singlebitns|
|freq|INTEGER|AI Corefrequencyratevalue, singlebitMHz|

**ACC\_PMU**

ACC\_PMUData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 28**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|accId|INTEGER|addspeedadapterID|
|readBwLevel|INTEGER|DVPPandDSAaddspeedadapterreadbandwidthwidthofetclevel|
|writeBwLevel|INTEGER|DVPPandDSAaddspeedadaptercomposebandwidthwidthofetclevel|
|readOstLevel|INTEGER|DVPPandDSAaddspeedadapterreadandissueofetclevel|
|writeOstLevel|INTEGER|DVPPandDSAaddspeedadaptercomposeandissueofetclevel|
|timestampNs|NUMERIC|thisregiontimebetween, singlebitns|
|deviceId|INTEGER|DeviceID|

**SOC\_BANDWIDTH\_LEVEL**

SoCbandwidthwidthetclevelinformationinformation. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 29**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|l2BufferBwLevel|INTEGER|L2 Bufferbandwidthwidthetclevel|
|mataBwLevel|INTEGER|Matabandwidthwidthetclevel|
|timestampNs|NUMERIC|thisregiontimebetween, singlebitns|
|deviceId|INTEGER|DeviceID|

**NIC**

eachcounttimebetweensectionpointnetworknetworkinformationinformationData. 

Controlopenrelated: 

- msprofcommandcommandof--sys-io-profiling, --sys-io-sampling-freq
- Ascend PyTorch Profilerofsys\_io

**table 30**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|bandwidth|INTEGER|bandwidthwidth, singlebitByte/s|
|rxPacketRate|NUMERIC|receivePackagespeedrate, singlebitpacket/s|
|rxByteRate|NUMERIC|connectreceivecharactersectionspeedrate, singlebitByte/s|
|rxPackets|INTEGER|accumulatecalculatereceivePackagenumberamount, singlebitpacket|
|rxBytes|INTEGER|accumulatecalculateconnectreceivecharactersectionnumberamount, singlebitByte|
|rxErrors|INTEGER|accumulatecalculateconnectreceiveerrorerrorPackagenumberamount, singlebitpacket|
|rxDropped|INTEGER|accumulatecalculateconnectreceivelosePackagenumberamount, singlebitpacket|
|txPacketRate|NUMERIC|issuePackagespeedrate, singlebitpacket/s|
|txByteRate|NUMERIC|issuepresentcharactersectionspeedrate, singlebitByte/s|
|txPackets|INTEGER|accumulatecalculateissuePackagenumberamount, singlebitpacket|
|txBytes|INTEGER|accumulatecalculateissuepresentcharactersectionnumberamount, singlebitByte|
|txErrors|INTEGER|accumulatecalculateissuepresenterrorerrorPackagenumberamount, singlebitpacket|
|txDropped|INTEGER|accumulatecalculateissuepresentlosePackagenumberamount, singlebitpacket|
|funcId|INTEGER|Sidemouthsign|

**ROCE**

RoCEthroughinformationInterfacebandwidthwidthData. 

Controlopenrelated: 

- msprofcommandcommandof--sys-io-profiling, --sys-io-sampling-freq
- Ascend PyTorch Profilerofsys\_io

**table 31**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|bandwidth|INTEGER|bandwidthwidth, singlebitByte/s|
|rxPacketRate|NUMERIC|receivePackagespeedrate, singlebitpacket/s|
|rxByteRate|NUMERIC|connectreceivecharactersectionspeedrate, singlebitByte/s|
|rxPackets|INTEGER|accumulatecalculatereceivePackagenumberamount, singlebitpacket|
|rxBytes|INTEGER|accumulatecalculateconnectreceivecharactersectionnumberamount, singlebitByte|
|rxErrors|INTEGER|accumulatecalculateconnectreceiveerrorerrorPackagenumberamount, singlebitpacket|
|rxDropped|INTEGER|accumulatecalculateconnectreceivelosePackagenumberamount, singlebitpacket|
|txPacketRate|NUMERIC|issuePackagespeedrate, singlebitpacket/s|
|txByteRate|NUMERIC|issuepresentcharactersectionspeedrate, singlebitByte/s|
|txPackets|INTEGER|accumulatecalculateissuePackagenumberamount, singlebitpacket|
|txBytes|INTEGER|accumulatecalculateissuepresentcharactersectionnumberamount, singlebitByte|
|txErrors|INTEGER|accumulatecalculateissuepresenterrorerrorPackagenumberamount, singlebitpacket|
|txDropped|INTEGER|accumulatecalculateissuepresentlosePackagenumberamount, singlebitpacket|
|funcId|INTEGER|Sidemouthsign|

**LLC**

threelevelslowkeepbandwidthwidthData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 32**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|llcId|INTEGER|threelevelslowkeepID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|hitRate|NUMERIC|threelevelslowkeepcommandmiddlerate(100%)|
|throughput|NUMERIC|threelevelslowkeepinputoutputamount, singlebitByte/s|
|mode|INTEGER|modelformula, Used forregiondistributeisreadorcompose, STRING_IDS(mode)|

**TASK\_PMU\_INFO**

CalculationOperatorofPMUData. 

Controlopenrelated: 

- msprofcommandcommandof--ai-core, --aic-mode=task-basedopenrelatedControloughttableGenerate, --aic-metricsopenrelatedControltoolbodyDataCollection
- Ascend PyTorch Profilerofaic\_metrics
- MindSpore Profilerofaic\_metrics

onlyAtlas 200I/500 A2 pushmanageproduceproductandAtlas A2 trainpracticesystemcolumnproduceproduct/Atlas A2 pushmanagesystemcolumnproduceproductSupportCollectionoughtData. 

**table 33**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|globalTaskId|INTEGER|GlobalOperatorTaskID, Used forrelatedconnectTASKtable|
|name|INTEGER|PMU metricfingerstandardname, STRING_IDS(name)|
|value|NUMERIC|Correspondingfingerstandardnameofnumbervalue|

**SAMPLE\_PMU\_TIMELINE**

sample-basedofPMUData, Used fortimelinetypeofDatapresentappear. 

Controlopenrelated: 

- msprofcommandcommandof--ai-core, --aic-mode=sample-basedopenrelatedControloughttableGenerate, --aic-metricsopenrelatedControltoolbodyDataCollection
- Ascend PyTorch Profilerofaic\_metrics
- MindSpore Profilerofaic\_metrics

**table 34**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|totalCycle|INTEGER|Correspondingcoreintimebetweensliceaboveofcyclenumber|
|usage|NUMERIC|Correspondingcoreintimebetweensliceaboveofutilizeuserate (100%) |
|freq|NUMERIC|Correspondingcoreintimebetweensliceaboveoffrequencyrate, singlebitMHz|
|coreId|INTEGER|coreId|
|coreType|INTEGER|coretypetype(AICorAIV), STRING_IDS(coreType)|

**SAMPLE\_PMU\_SUMMARY**

sample-basedofPMUData, Used forsummarytypeofDatapresentappear. 

Controlopenrelated: 

- msprofcommandcommandof--ai-core, --aic-mode=sample-basedopenrelatedControloughttableGenerate, --aic-metricsopenrelatedControltoolbodyDataCollection
- Ascend PyTorch Profilerofaic\_metrics
- MindSpore Profilerofaic\_metrics

**table 35**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|metric|INTEGER|PMU metricfingerstandardname, STRING_IDS(metric)|
|value|NUMERIC|Correspondingfingerstandardnameofnumbervalue|
|coreId|INTEGER|coreId|
|coreType|INTEGER|coretypetype(AICorAIV), STRING_IDS(coreType)|

**NPU\_MEM**

NPUMemoryoccupyuseData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 36**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|type|INTEGER|eventtypetype, appordevice, STRING_IDS(type)|
|ddr|NUMERIC|ddroccupyuselargesmall, singlebitByte|
|hbm|NUMERIC|hbmoccupyuselargesmall, singlebitByte|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|deviceId|INTEGER|DeviceID|

**NPU\_MODULE\_MEM**

NPUComponentsMemoryoccupyuseData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 37**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|moduleId|INTEGER|Componentstypetype, ENUM_MODULE(moduleId)|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|totalReserved|NUMERIC|Memoryoccupyuselargesmall, singlebitByte|
|deviceId|INTEGER|DeviceID|

**NPU\_OP\_MEM**

CANNOperatorMemoryoccupyuseData, onlyGEOperatorSupport. 

by--task-memoryopenrelatedControl. 

**table 38**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|operatorName|INTEGER|Operatornamecharacter, STRING_IDS(operatorName)|
|addr|INTEGER|Memoryapplypleaseexplainreleasefirstregionaddress|
|type|INTEGER|Used forregiondistributeapplypleaseorisexplainrelease, STRING_IDS(type)|
|size|INTEGER|applypleaseofMemorylargesmall, singlebitByte|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|globalTid|INTEGER|oughtitemrememberdocumentofGlobalTID. high32bit: PID, low32bit: TID|
|totalAllocate|NUMERIC|totalbodyalreadydistributematchofMemorylargesmall, singlebitByte|
|totalReserve|NUMERIC|totalbodymaintainhaveofMemorylargesmall, singlebitByte|
|component|INTEGER|Componentsname, STRING_IDS(component)|
|deviceId|INTEGER|DeviceID|

**HBM**

sliceaboveMemoryreadcomposespeedrateData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 39**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|bandwidth|NUMERIC|bandwidthwidth, singlebitByte/s|
|hbmId|INTEGER|MemoryvisitasksingleunitID|
|type|INTEGER|Used forregiondistributereadorcompose, STRING_IDS(type)|

**DDR**

sliceaboveMemoryreadcomposespeedrateData. 

by--sys-hardware-mem, --sys-hardware-mem-freqopenrelatedControl. 

**table 40**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|read|NUMERIC|MemoryReadbandwidthwidth, singlebitByte/s|
|write|NUMERIC|Memorycomposeinputbandwidthwidth, singlebitByte/s|

**HCCS**

HCCSsetmatchthroughinformationbandwidthwidthData. 

Controlopenrelated: 

- msprofcommandcommandof--sys-interconnection-profiling, --sys-interconnection-freq
- Ascend PyTorch Profilerofsys\_interconnection

**table 41**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|txThroughput|NUMERIC|issuepresentbandwidthwidth, singlebitByte/s|
|rxThroughput|NUMERIC|connectreceivebandwidthwidth, singlebitByte/s|

**PCIE**

PCIebandwidthwidthData. 

Controlopenrelated: 

- msprofcommandcommandof--sys-interconnection-profiling, --sys-interconnection-freq
- Ascend PyTorch Profilerofsys\_interconnection

**table 42**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|thisregiontimebetween, singlebitns|
|txPostMin|NUMERIC|issuepresentSidePCIe PostDatatransferoutputbandwidthwidthmostsmallvalue, singlebitByte/s|
|txPostMax|NUMERIC|issuepresentSidePCIe PostDatatransferoutputbandwidthwidthmostlargevalue, singlebitByte/s|
|txPostAvg|NUMERIC|issuepresentSidePCIe PostDatatransferoutputbandwidthwidthaverageaveragevalue, singlebitByte/s|
|txNonpostMin|NUMERIC|issuepresentSidePCIe Non-PostDatatransferoutputbandwidthwidthmostsmallvalue, singlebitByte/s|
|txNonpostMax|NUMERIC|issuepresentSidePCIe Non-PostDatatransferoutputbandwidthwidthmostlargevalue, singlebitByte/s|
|txNonpostAvg|NUMERIC|issuepresentSidePCIe Non-PostDatatransferoutputbandwidthwidthaverageaveragevalue, singlebitByte/s|
|txCplMin|NUMERIC|issuepresentSideconnectreceivecomposepleaserequestofcompletedDataPackagemostsmallvalue, singlebitByte/s|
|txCplMax|NUMERIC|issuepresentSideconnectreceivecomposepleaserequestofcompletedDataPackagemostlargevalue, singlebitByte/s|
|txCplAvg|NUMERIC|issuepresentSideconnectreceivecomposepleaserequestofcompletedDataPackageaverageaveragevalue, singlebitByte/s|
|txNonpostLatencyMin|NUMERIC|issuepresentSidePCIe Non-Postmodelformulaunderoftransferoutputtimeextendmostsmallvalue, singlebitns|
|txNonpostLatencyMax|NUMERIC|issuepresentSidePCIe Non-Postmodelformulaunderoftransferoutputtimeextendmostlargevalue, singlebitns|
|txNonpostLatencyAvg|NUMERIC|issuepresentSidePCIe Non-Postmodelformulaunderoftransferoutputtimeextendaverageaveragevalue, singlebitns|
|rxPostMin|NUMERIC|connectreceiveSidePCIe PostDatatransferoutputbandwidthwidthmostsmallvalue, singlebitByte/s|
|rxPostMax|NUMERIC|connectreceiveSidePCIe PostDatatransferoutputbandwidthwidthmostlargevalue, singlebitByte/s|
|rxPostAvg|NUMERIC|connectreceiveSidePCIe PostDatatransferoutputbandwidthwidthaverageaveragevalue, singlebitByte/s. |
|rxNonpostMin|NUMERIC|connectreceiveSidePCIe Non-PostDatatransferoutputbandwidthwidthmostsmallvalue, singlebitByte/s|
|rxNonpostMax|NUMERIC|connectreceiveSidePCIe Non-PostDatatransferoutputbandwidthwidthmostlargevalue, singlebitByte/s|
|rxNonpostAvg|NUMERIC|connectreceiveSidePCIe Non-PostDatatransferoutputbandwidthwidthaverageaveragevalue, singlebitByte/s|
|rxCplMin|NUMERIC|connectreceiveSidereceivetocomposepleaserequestofcompletedDataPackagemostsmallvalue, singlebitByte/s|
|rxCplMax|NUMERIC|connectreceiveSidereceivetocomposepleaserequestofcompletedDataPackagemostlargevalue, singlebitByte/s|
|rxCplAvg|NUMERIC|connectreceiveSidereceivetocomposepleaserequestofcompletedDataPackageaverageaveragevalue, singlebitByte/s|

**META\_DATA**

BaseData, whenpreviousonlykeepkeepVersionsigninformationinformation. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. 

**table 43**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|name|TEXT|characterparagraphname|
|value|TEXT|numbervalue|

**table 44**  insidecontent

|name|containmeaning|
|--|--|
|SCHEMA_VERSION|totalVersionsign, if1.0.2|
|SCHEMA_VERSION_MAJOR|largeVersionsign, if1, onlywhenDatabaseformatformulakeepinweightcomposeorweightstructuretimeupdatemodify|
|SCHEMA_VERSION_MINOR|middleVersionsign, if0, whenupdatemodifycolumnortypetypetimeupdatemodify, keepinCompatibilityaskproblem|
|SCHEMA_VERSION_MICRO|smallVersionsign, if2, whenUpdatetabletimeallableupdatemodify, nottoolhaveCompatibilityaskproblem|

**MSTX\_EVENTS**

mstxInterfaceCollectionofHostsideData, DevicesideDatainTASKtablemiddleadjustmatch. 

by--msproftxopenrelatedControltableformatOutput, mstxInterfaceControlDataofCollection. 

**table 45**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|startNs|INTEGER|HostsidetxprintpointDataopenbegintimebetween, singlebitns|
|endNs|INTEGER|HostsidetxprintpointDataconclusionendtimebetween, singlebitns|
|eventType|INTEGER|HostsidetxprintpointDatatypetype, ENUM_MSTX_EVENT_TYPE(eventType)|
|rangeId|INTEGER|HostsiderangetypetypetxDataCorrespondingofrange ID|
|category|INTEGER|HostsidetxDataallattributeofdistributetypeID|
|message|INTEGER|HostsidetxprintpointDatacarrybandwidthinformationinformation, STRING_IDS(message)|
|globalTID|INTEGER|HostsidetxprintpointDataopenbeginlineprocessofGlobalTID|
|endGlobalTid|INTEGER|HostsidetxprintpointDataconclusionendlineprocessofGlobalTID|
|domainId|INTEGER|HostsidetxprintpointDataallattributedomainofdomainID|
|connectionId|INTEGER|HostsidetxprintpointDataofrelatedconnectID, TASK(connectionId)|

**COMMUNICATION\_SCHEDULE\_TASK\_INFO**

throughinformationadjustdegreeDescriptioninformationinformation, whenpreviousonlyneedlepairAI CPUthroughinformationOperatorofDescription. 

noCorrespondingopenrelated, guideoutputmsprof\_\{timebetweenstab\}.dbfiletimesilentrecognizeGenerate. requiresCollectionEnvironmentmiddlePackagecontainAI CPUthroughinformationOperator. 

**table 46**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|name|INTEGER|Operatorname, STRING_IDS(name)|
|globalTaskId|INTEGER|mainkey, GlobalOperatorTaskID, Used forrelatedconnectTASKtable|
|taskType|INTEGER|HostExecuteoughtOperatorofaddspeedadaptertypetype, STRING_IDS(taskType)|
|opType|INTEGER|Operatortypetype, STRING_IDS(opType)|

**MEMCPY\_INFO**

DescriptionmemcpyRelatedOperatorofcopyshellDataamountandcopyshellmethoddirection. 

by--runtime-apiopenrelatedControl. 

**table 47**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|globalTaskId|NUMERIC|mainkey, GlobalOperatorTaskID, Used forrelatedconnectTASK|
|size|NUMERIC|copyshellofDataamount|
|memcpyOperation|NUMERIC|copyshelltypetype, STRING_IDS(memcpyDirection)|

**CPU\_USAGE**

HostsideCPUutilizeuserateData. 

by--host-sys=cpuopenrelatedControl. 

**table 48**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|timestampNs|NUMERIC|adoptsampletimeofthisregiontimebetween, singlebitns|
|cpuId|NUMERIC|cpucompilesign|
|usage|NUMERIC|utilizeuserate(%)|

**HOST\_MEM\_USAGE**

HostsideMemoryutilizeuserateData. 

by--host-sys=memopenrelatedControl. 

**table 49**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|timestampNs|NUMERIC|adoptsampletimeofthisregiontimebetween, singlebitns|
|usage|NUMERIC|utilizeuserate(%)|

**HOST\_DISK\_USAGE**

HostsidemagneticdiskI/OutilizeuserateData. 

by--host-sys=diskopenrelatedControl. 

**table 50**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|timestampNs|NUMERIC|adoptsampletimeofthisregiontimebetween, singlebitns|
|readRate|NUMERIC|magneticdiskreadspeedrate, singlebitB/s|
|writeRate|NUMERIC|magneticdiskcomposespeedrate, singlebitB/s|
|usage|NUMERIC|utilizeuserate(%)|

**HOST\_NETWORK\_USAGE**

HostsidesystemstatisticslevelcategoryofnetworknetworkI/OutilizeuserateData. 

by--host-sys=networkopenrelatedControl. 

**table 51**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|timestampNs|NUMERIC|adoptsampletimeofthisregiontimebetween, singlebitns|
|usage|NUMERIC|utilizeuserate(%)|
|speed|NUMERIC|networknetworkUsagespeedrate, singlebitB/s|

**OSRT\_API**

HostsidesyscallandpthreadcallData. 

by--host-sys=osrtopenrelatedControl. 

**table 52**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|name|INTEGER|OS Runtime APIInterfacename|
|globalTid|NUMERIC|oughtAPIallinlineprocessofGlobalTID. high32bit: PID, low32bit: TID|
|startNs|INTEGER|APIofopenbegintimebetween, singlebitns|
|endNs|INTEGER|APIofconclusionendtimebetween, singlebitns|

**NETDEV\_STATS**

throughexceedHardwareadoptsamplebandwidthwidthabilityforce, canin order topartdistributerecognizecategorythroughinformationaskproblem, astotalviewitem, initialsteparrangesearchthroughinformationaskproblem, ifoutputappearthroughinformationTime consumptiondifferentoften, immediatecanoptimizefirstarrangesearchiswhetherasnetworknetworkholdblockguideconsistent. 

Controlopenrelated: 

- msprofcommandcommandof--sys-io-profiling, --sys-io-sampling-freq
- Ascend PyTorch Profilerofsys\_io
- MindSpore Profilerofsys\_io

**table 53**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|deviceId|INTEGER|DeviceID|
|timestampNs|INTEGER|adoptsampletimeofthisregiontimebetween, singlebitns|
|macTxPfcPkt|INTEGER|MACissuepresentofPFCframenumber|
|macRxPfcPkt|INTEGER|MACconnectreceiveofPFCframenumber|
|macTxByte|INTEGER|MACissuepresentofcharactersectionnumber|
|macTxBandwidth|NUMERIC|MACissuepresentbandwidthwidth, singlebitByte / s|
|macRxByte|INTEGER|MACconnectreceiveofcharactersectionnumber|
|macRxBandwidth|NUMERIC|MACconnectreceivebandwidthwidth, singlebitByte / s|
|macTxBadByte|INTEGER|MACissuepresentofbadPackagereportdocumentcharactersectionnumber|
|macRxBadByte|INTEGER|MACconnectreceiveofbadPackagereportdocumentcharactersectionnumber|
|roceTxPkt|INTEGER|RoCEEissuepresentofreportdocumentnumber|
|roceRxPkt|INTEGER|RoCEEconnectreceiveofreportdocumentnumber|
|roceTxErrPkt|INTEGER|RoCEEissuepresentofbadPackagereportdocumentnumber|
|roceRxErrPkt|INTEGER|RoCEEconnectreceiveofbadPackagereportdocumentnumber|
|roceTxCnpPkt|INTEGER|RoCEEissuepresentofCNPtypetypereportdocumentnumber|
|roceRxCnpPkt|INTEGER|RoCEEconnectreceiveofCNPtypetypereportdocumentnumber|
|roceNewPktRty|INTEGER|RoCEEissuepresentofexceedtimeweighttransferofnumberamount|
|nicTxByte|INTEGER|NICissuepresentofcharactersectionnumber|
|nicTxBandwidth|NUMERIC|NICissuepresentbandwidthwidth, singlebitByte / s|
|nicRxByte|INTEGER|NICconnectreceiveofcharactersectionnumber|
|nicRxBandwidth|NUMERIC|NICconnectreceivebandwidthwidth, singlebitByte / s|

**RANK\_DEVICE\_MAP**

rankIdanddeviceIdofreflectshootrelatedsystemData. 

noCorrespondingopenrelated, guideoutputascend\_pytorch\_profiler\_\{Rank\_ID\}.dbfiletimesilentrecognizeGenerate. 

**table 54**  formatformula

|characterparagraphname|typetype|containmeaning|
|--|--|--|
|rankId|INTEGER|getvaluesoliddefineas-1. |
|deviceId|INTEGER|sectionpointaboveofDeviceID, displayshowas-1timetableshownotCollectiontodeviceId. |


