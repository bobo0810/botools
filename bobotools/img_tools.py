import hashlib
from tqdm import tqdm
import numpy as np
import cv2
import torch
import base64
import urllib.request

class Img_Tools(object):
    """
    Img工具类
    """

    def __init__(self):
        pass
    
    @staticmethod
    def read_web_img(image_url=None,image_file=None,image_base64=None,url_time_out=10):
        '''
        参数三选一，当传入多个参数，仅返回最高优先级的图像

        优先级： 文件 > base64 > url 
        
        url_time_out : URL下载耗时限制，默认10秒
        '''
        if image_file:
            try:
                img = cv2.imdecode(np.frombuffer(image_file, np.uint8), cv2.IMREAD_COLOR)
                if img.any():
                    return img
                else:
                    return 'IMAGE_ERROR_UNSUPPORTED_FORMAT'
            except:
                return 'IMAGE_ERROR_UNSUPPORTED_FORMAT'

        elif image_base64:
            try:
                img = base64.b64decode(image_base64)
                img_array = np.frombuffer(img, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if img.any():
                    return img
                else:
                    return 'IMAGE_ERROR_UNSUPPORTED_FORMAT'
            except:
                return 'IMAGE_ERROR_UNSUPPORTED_FORMAT'
        elif image_url:
            try:
                resp = urllib.request.urlopen(image_url,time_out=url_time_out)
            except:
                return 'URL_DOWNLOAD_TIMEOUT'
            try:
                image = np.asarray(bytearray(resp.read()), dtype="uint8")
                img = cv2.imdecode(image, cv2.IMREAD_COLOR)
                if img.any():
                    return img
                else:
                    return 'IMAGE_ERROR_UNSUPPORTED_FORMAT'
            except:
                return 'INVALID_IMAGE_URL'
        else:
            return 'MISSING_ARGUMENTS'

    @staticmethod
    def plot_bbox(img, bbox, name, prob):
        """
        绘制bbox后原格式返回

        img(numpy): cv2读取的图像[H,W,C]
        bbox(list):  锚框归一化后的坐标[N,4]. 即中心点坐标xy、锚框宽高wh. eg:[[0.61,0.64,0.12,0.20],...]
        name(list): 锚框对应类别[N]. eg:['cat', 'dog', ...]
        prob(list): 锚框对应概率[N]. eg:[0.9, 0.8, ...]

        return
        img(numpy): 已绘制的图像[H,W,C]
        """
        assert type(img) is np.ndarray
        assert len(bbox) == len(name) == len(prob)

        height, width, _ = img.shape
        img = np.ascontiguousarray(img)  # 内存连续

        lw = 3  # 线条宽度宽
        color, txt_color = (0, 0, 255), (0, 0, 255)  # 锚框、文字颜色
        tl = round(0.002 * (width + height) / 2) + 1  # 锚框、文字的粗细

        for (x, y, w, h), name_i, prob_i in zip(bbox, name, prob):
            c1 = int((x - w / 2) * width), int((y - h / 2) * height)
            c2 = int((x + w / 2) * width), int((y + h / 2) * height)
            cv2.rectangle(
                img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA
            )  # 绘制锚框
            cv2.putText(
                img,
                name_i + "_" + str(round(prob_i, 2)),
                (c1[0], c1[1] - 2),
                0,
                lw / 3,
                txt_color,
                thickness=tl,
                lineType=cv2.LINE_AA,
            )  # 绘制类别概率
        return img

    @staticmethod
    def filter_md5(imgs_list, compare_list=[]):
        """
        基于md5对imgs_list图像自身去重，返回重复图像的列表
        compare_list(可选): 基于对比库再去重。

        若文件读取出错，则过滤掉
        """

        ###########################内部方法######################################
        def get_md5(file):
            """计算md5"""
            file = open(file, "rb")
            md5 = hashlib.md5(file.read())
            file.close()
            return md5.hexdigest()

        def get_md5lib(imgs_list):
            """构建md5底库"""
            print("start generate md5lib...")
            md5_lib = []
            for img_path in tqdm(imgs_list):
                try:
                    md5_lib.append(get_md5(img_path))
                except:
                    continue
            return md5_lib

        def query_md5(imgs_list, md5_lib):
            print("start filter md5...")
            rm_list = []
            for img_path in tqdm(imgs_list):
                try:
                    md5 = get_md5(img_path)
                    if md5 not in md5_lib:
                        md5_lib.append(md5)
                    else:
                        rm_list.append(img_path)
                except:
                    continue
            return rm_list

        #################################################################

        assert type(imgs_list) is list
        assert type(compare_list) is list
        md5_lib = []
        # 构建对比库
        if len(compare_list) > 0:
            md5_lib.extend(get_md5lib(compare_list))
        return query_md5(imgs_list, md5_lib)

    @staticmethod
    def verify_integrity(imgs_list):
        """
        验证图像完整性

        imgs_list(list): 包含图像绝对路径的列表。 eg:[/home/a.jpg,...]

        return
        error_list(list): 错误图像的列表。eg:[/home/a.jpg,...]
        """
        error_list = []
        for img_path in tqdm(imgs_list):
            try:
                image = cv2.imread(img_path, cv2.IMREAD_COLOR)
                assert type(image) is np.ndarray
            except:
                error_list.append(img_path)
        return error_list

    @staticmethod
    def tensor2img(
        tensor, mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225), BCHW2BHWC=False
    ):
        """
        Tenso恢复为图像，用于可视化
        反归一化、RGB->BGR

        tensor: Tensor,形状[B,C,H,W]
        BCHW2BHWC: (可选)是否交换Tensor维度

        返回值
        imgs: Tensor 默认[B,C,H,W]。当BCHW2BHWC=Ture,则返回[B,H,W,C]
        """
        B, C, H, W = tensor.shape

        t_mean = torch.FloatTensor(mean).view(C, 1, 1).expand(3, H, W)
        t_std = torch.FloatTensor(std).view(C, 1, 1).expand(3, H, W)

        tensor = tensor * t_std.to(tensor) + t_mean.to(tensor)  # 反归一化
        tensor = tensor[:, [2, 1, 0], :, :]  # RGB->BGR
        if BCHW2BHWC:
            tensor = tensor.permute(0, 2, 3, 1)
        return tensor
