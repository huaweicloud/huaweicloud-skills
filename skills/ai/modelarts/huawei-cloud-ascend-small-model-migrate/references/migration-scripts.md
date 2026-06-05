# MigrationVerificationScriptsReference

## YOLO systemcolumnVerification

```python
#!/usr/bin/env python3
"""YOLO AscendMigrationVerificationScripts"""

import torch
import torch_npu
from ultralytics import YOLO
import time

def check_npu():
    """Check NPU Environment"""
    print("=" * 50)
    print("NPU EnvironmentCheck")
    print("=" * 50)
    print(f"torch_npu Version: {torch_npu.__version__}")
    print(f"NPU canuse: {torch.npu.is_available()}")
    print(f"NPU numberamount: {torch.npu.device_count()}")
    for i in range(torch.npu.device_count()):
        print(f"  NPU {i}: {torch.npu.get_device_name(i)}")
    print()

def test_inference(model_path, image_path, device='npu:0'):
    """pushmanageTesting"""
    print("=" * 50)
    print("pushmanageTesting")
    print("=" * 50)
    
    # LoadModel
    print(f"LoadModel: {model_path}")
    model = YOLO(model_path)
    
    # pushmanage
    print(f"pushmanagefigureslice: {image_path}")
    print(f"Device: {device}")
    
    # prepassionate
    model(image_path, device=device)
    
    # PerformanceTesting
    times = []
    for i in range(100):
        start = time.time()
        result = model(image_path, device=device)
        times.append((time.time() - start) * 1000)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    fps = 1000 / avg_time
    
    print()
    print("PerformanceResult:")
    print(f"  averageaverageTime consumption: {avg_time:.2f} ms")
    print(f"  mostsmallTime consumption: {min_time:.2f} ms")
    print(f"  mostlargeTime consumption: {max_time:.2f} ms")
    print(f"  FPS: {fps:.1f}")
    print()
    
    # checktestResult
    print("checktestResult:")
    for r in result:
        for box in r.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            print(f"  typecategory {cls}: placeinformationdegree {conf:.2f}")
    print()
    
    return {
        'avg_time': avg_time,
        'fps': fps,
        'success': True
    }

if __name__ == '__main__':
    check_npu()
    result = test_inference('yolov8n.pt', 'bus.jpg')
    print(f"MigrationVerification: {'becomefunction' if result['success'] else 'lossfailure'}")
```

## ResNet systemcolumnVerification

```python
#!/usr/bin/env python3
"""ResNet AscendMigrationVerificationScripts"""

import torch
import torch_npu
import torchvision.models as models
from torchvision import transforms
from PIL import Image
import time

def check_npu():
    """Check NPU Environment"""
    print("=" * 50)
    print("NPU EnvironmentCheck")
    print("=" * 50)
    print(f"NPU canuse: {torch.npu.is_available()}")
    print(f"NPU numberamount: {torch.npu.device_count()}")
    print()

def test_inference(model_name='resnet50', image_path='test.jpg'):
    """pushmanageTesting"""
    device = 'npu:0'
    
    # LoadModel
    print(f"LoadModel: {model_name}")
    model = getattr(models, model_name)(pretrained=True)
    model = model.to(device)
    model.eval()
    
    # prehandlemanage
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225]),
    ])
    
    # Loadfigureslice
    image = Image.open(image_path).convert('RGB')
    input_tensor = preprocess(image).unsqueeze(0).to(device)
    
    # prepassionate
    with torch.no_grad():
        _ = model(input_tensor)
    
    # PerformanceTesting
    torch.npu.synchronize()
    times = []
    for _ in range(100):
        start = time.time()
        with torch.no_grad():
            output = model(input_tensor)
        torch.npu.synchronize()
        times.append((time.time() - start) * 1000)
    
    avg_time = sum(times) / len(times)
    fps = 1000 / avg_time
    
    print(f"averageaverageTime consumption: {avg_time:.2f} ms")
    print(f"FPS: {fps:.1f}")
    
    # pretestResult
    _, pred = torch.max(output, 1)
    print(f"pretesttypecategory: {pred.item()}")

if __name__ == '__main__':
    check_npu()
    test_inference()
```

## throughuseVerificationTemplate

```python
#!/usr/bin/env python3
"""throughuseModelVerificationTemplate"""

import torch
import torch_npu
import time

def verify_model(model_class, model_args, input_shape, device='npu:0'):
    """
    throughuseVerificationfunctionnumber
    
    Args:
        model_class: Modeltype
        model_args: ModelInitializationparameternumber
        input_shape: outputinputshapestatus (batch, channels, height, width)
        device: Device
    """
    print("=" * 50)
    print("ModelVerification")
    print("=" * 50)
    
    # Check NPU
    print(f"NPU canuse: {torch.npu.is_available()}")
    print(f"Device: {device}")
    
    # LoadModel
    model = model_class(**model_args)
    model = model.to(device)
    model.eval()
    print(f"ModelLoadbecomefunction")
    
    # Createoutputinput
    input_tensor = torch.randn(input_shape).to(device)
    
    # prepassionate
    with torch.no_grad():
        _ = model(input_tensor)
    
    # PerformanceTesting
    torch.npu.synchronize()
    times = []
    for _ in range(100):
        start = time.time()
        with torch.no_grad():
            output = model(input_tensor)
        torch.npu.synchronize()
        times.append((time.time() - start) * 1000)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    fps = 1000 / avg_time
    
    print()
    print("PerformanceResult:")
    print(f"  averageaverageTime consumption: {avg_time:.2f} ms")
    print(f"  mostsmallTime consumption: {min_time:.2f} ms")
    print(f"  mostlargeTime consumption: {max_time:.2f} ms")
    print(f"  FPS: {fps:.1f}")
    
    return {
        'avg_time': avg_time,
        'fps': fps,
        'success': True
    }
```
