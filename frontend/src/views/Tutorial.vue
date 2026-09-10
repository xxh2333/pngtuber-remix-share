<template>
  <div class="tutorial-page">
    <el-card>
      <h2>📚 新手教程</h2>

      <el-divider />

      <h3>一、什么是 PNGTuber？</h3>
      <p>PNGTuber 是一种基于 PNG 图片的虚拟主播（VTuber）形式，通过多张表情图片在麦克风音量触发下切换，实现简单的动态效果。相比 Live2D 模型，PNGTuber 制作门槛低、资源占用小。</p>

      <h3>二、PNGTuber 模型制作规范</h3>
      <el-steps :active="3" finish-status="success" align-center>
        <el-step title="准备素材" description="绘制角色表情 PNG 图，建议尺寸 512x512 或 1024x1024，背景透明" />
        <el-step title="命名图层" description="默认表情命名为 normal.png，其他如 happy.png、sad.png 等" />
        <el-step title="打包 ZIP" description="将所有 PNG 放入一个文件夹，压缩为 ZIP 格式" />
        <el-step title="上传分享" description="在本站上传，填写图源自与介绍" />
      </el-steps>

      <h3>三、ZIP 包结构示例</h3>
      <pre class="code-block">
mymodel.zip
├── normal.png      # 默认表情（必填，用于生成预览图）
├── happy.png       # 开心表情
├── sad.png         # 难过表情
└── config.json     # 可选配置文件
      </pre>

      <h3>四、上传步骤</h3>
      <ol>
        <li>点击左侧「上传」进入上传页</li>
        <li>填写标题、介绍、标签</li>
        <li><strong>填写「图源自」</strong>（必填）：注明图片/模型的来源，保护原作者权益</li>
        <li>选择是否允许他人二改你的作品</li>
        <li>上传 ZIP 包，提交即可</li>
      </ol>

      <h3>五、关于二改</h3>
      <el-alert type="info" :closable="false" style="margin-bottom: 12px">
        <p><strong>允许二改</strong>：其他用户可基于你的作品上传二改版本，二改作品会挂载在原作品详情页的「二改作品」子栏中。</p>
        <p><strong>禁止二改</strong>：他人无法将你的作品设为二改父作品。</p>
      </el-alert>
      <p>二改作品同样需要填写「图源自」，建议注明原作品链接。</p>

      <h3>六、禁止内容</h3>
      <el-alert type="error" :closable="false">
        <ul style="margin:0;padding-left:20px">
          <li>禁止上传 AI 模型文件（.pt / .onnx / .safetensors / .bin 等）</li>
          <li>禁止上传侵权内容</li>
          <li>禁止上传违规违法内容</li>
        </ul>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
</script>

<style scoped>
.tutorial-page {
  max-width: 800px;
  margin: 0 auto;
}
.code-block {
  background: #1f2937;
  color: #e5e7eb;
  padding: 16px;
  border-radius: 6px;
  font-family: monospace;
  line-height: 1.6;
}
ol li {
  margin-bottom: 6px;
}
</style>
