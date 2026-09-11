<template>
  <div class="tutorial-page">
    <el-card>
      <h2>📚 新手教程</h2>
      <p class="lead">本教程帮助你从零开始：准备素材 → 下载桌宠软件 → 制作模型 → 上传本站分享。</p>

      <el-divider />

      <h3>一、什么是 PNGTuber？</h3>
      <p>PNGTuber 是一种基于静态图片的虚拟主播（VTuber）形式：软件根据麦克风音量在「闭嘴 / 张嘴」等状态间切换图片，即可实现简单的直播形象。相比 Live2D / 3D 模型，PNGTuber 制作门槛低、资源占用小，还能做成放在桌面上的「桌宠」。</p>
      <p>本站分享的模型文件为 <el-tag size="small">.pngRemix</el-tag> 格式，由免费开源软件 <strong>PNGTube Remix</strong> 制作和打开。</p>

      <h3>二、需要准备什么</h3>
      <el-table :data="prepareList" stripe size="small" class="prepare-table">
        <el-table-column label="项目" prop="name" width="150" />
        <el-table-column label="说明" prop="desc" />
      </el-table>

      <h3>三、下载 PNGTube Remix（桌宠软件）</h3>
      <el-alert type="success" :closable="false" class="credit-alert">
        <p>
          <strong>软件名称：</strong>PNGTube Remix（基于 Godot 引擎，MIT 开源协议，商用 / 非商用均免费）<br />
          <strong>原作者：</strong>TheMime（GitHub：MudkipWorld）<br />
          <strong>官方下载地址：</strong>
          <el-link type="primary" href="https://mudkipworld.itch.io/pngremix" target="_blank">https://mudkipworld.itch.io/pngremix</el-link><br />
          <strong>GitHub 仓库 / 全部历史版本：</strong>
          <el-link type="primary" href="https://github.com/MudkipWorld/PNGTuber-Remix/releases" target="_blank">https://github.com/MudkipWorld/PNGTuber-Remix/releases</el-link>
        </p>
      </el-alert>
      <ol>
        <li>打开上方官方地址，点击 <strong>Download Now</strong>，下载 <strong>PNGTube-Remix (Windows)</strong> 压缩包（Linux 用户选 Linux 版；macOS 暂无官方构建）。</li>
        <li><strong>下载的是完整压缩包，不要下载 Source code（源码包）</strong>；将压缩包解压到一个固定文件夹，<strong>不要只把 exe 单独拖出来</strong>——它依赖同目录下的 .pck、.dll 等文件。</li>
        <li>运行文件夹里的 <code>PNGTube Remix.exe</code> 即可启动；启动后可选择「桌宠模式」或「直播模式」。</li>
        <li>双击 <code>.pngRemix</code> 模型文件，或在软件内 File → Open，即可加载模型。</li>
      </ol>
      <pre class="code-block">
📂 PNGTubeRemix Windows（解压后）
 ┣📄 PNGTube Remix.exe        ← 启动这个
 ┣📄 PNGTube Remix.console.exe
 ┣📄 PNGTube Remix.pck
 ┣📄 DefaultTraining.tres
 ┣📄 *.dll                    ← 依赖文件，缺一不可
 ┗📄 WebsocketDocumentation.txt
      </pre>

      <h3>四、制作属于自己的 .pngRemix 模型</h3>
      <el-steps :active="4" finish-status="success" align-center>
        <el-step title="准备角色素材" description="透明背景的 PNG / GIF 图层：身体、头发、睁眼、闭眼、张嘴、闭嘴等，分别导出" />
        <el-step title="导入编辑器" description="在 PNGTube Remix 中 File → Import 或直接把图片拖入图层树，按层级摆放" />
        <el-step title="设置状态" description="配置麦克风触发的状态切换（如说话时显示张嘴图），可加眨眼、晃动等效果" />
        <el-step title="保存模型" description="File → Save，得到 .pngRemix 模型文件，这就是要上传本站的文件" />
      </el-steps>
      <el-alert type="info" :closable="false">
        不会自己画也没关系：你可以使用其他作者<strong>明确允许二改</strong>的模型进行修改，但必须遵守对方的授权要求并保留署名。
      </el-alert>

      <h3>五、上传到本站分享</h3>
      <ol>
        <li><router-link to="/register">注册账号</router-link>并登录，点击左侧「上传」。</li>
        <li>填写标题、介绍、标签，便于他人搜索（可按作品名、作者名、标签搜索）。</li>
        <li><strong>「图源自」为必填项</strong>：写明素材 / 模型来源。若使用了他人素材，请注明原作者名字与原作品地址。</li>
        <li>选择授权方式（三档）：
          <ul>
            <li><el-tag type="success" size="small">允许下载和二创</el-tag> —— 他人可下载模型，也可在此基础上上传二创作品</li>
            <li><el-tag type="warning" size="small">仅允许下载</el-tag> / <el-tag type="warning" size="small">仅允许二创</el-tag></li>
            <li><el-tag type="danger" size="small">都不允许</el-tag> —— 仅在本站预览，不能下载也不能作为二创母本</li>
          </ul>
        </li>
        <li>选择 <code>.pngRemix</code> / <code>.pngtuber</code> / <code>.zip</code> 文件提交，单个文件最大 <strong>50MB</strong>，系统会自动生成预览图。</li>
      </ol>

      <h3>六、下载模型与二创规则</h3>
      <p>在作品详情页，作者标记为「允许下载」的作品会显示 <strong>下载模型</strong> 按钮，点击即可保存到本地，用 PNGTube Remix 打开。</p>
      <el-alert type="warning" :closable="false">
        <ul class="alert-list">
          <li>下载的模型版权归原作者所有，使用范围（能否商用、能否二改、能否转播）以作者标注的授权为准。</li>
          <li>发布二创作品需原作「允许二创」；上传时必须填写原作出处，二创作品会自动挂载在原作品详情页，可互相跳转。</li>
          <li>二创作品再次开放下载 / 二创，不能超越原作者给予的授权范围；请在介绍中说明你修改了什么。</li>
          <li>尊重原作者：保留署名、不冒充原作、不抹除来源信息。原作者 <strong>TheMime</strong> 的 PNGTube Remix 为免费开源软件，也欢迎在你的作品页注明使用了该软件。</li>
        </ul>
      </el-alert>

      <h3>七、禁止内容</h3>
      <el-alert type="error" :closable="false">
        <ul class="alert-list">
          <li>禁止上传 AI 模型文件（.pt / .onnx / .safetensors / .bin 等），本站仅接受桌宠模型文件。</li>
          <li>禁止上传侵权内容：未获授权的他人立绘、模型、付费素材，或将禁止二改的作品改头换面重新上传。</li>
          <li>禁止上传违法违规、涉黄涉暴等内容。</li>
          <li>违规作品将被删除，情节严重者封禁账号。</li>
        </ul>
      </el-alert>

      <el-divider />
      <p class="footnote">
        相关链接：
        <el-link type="primary" href="https://mudkipworld.itch.io/pngremix" target="_blank">PNGTube Remix 官方下载（itch.io）</el-link>
        ｜
        <el-link type="primary" href="https://github.com/MudkipWorld/PNGTuber-Remix" target="_blank">GitHub 开源仓库</el-link>
        ｜
        <el-link type="primary" href="https://mudkipworld.github.io/PNGRemix-Doc/" target="_blank">官方使用文档</el-link>
      </p>
    </el-card>
  </div>
</template>

<script setup>
const prepareList = [
  { name: '一台电脑', desc: 'Windows 10 / 11（官方也提供 Linux 版；macOS 暂无官方构建，需自行从源码编译）' },
  { name: '麦克风', desc: '直播 / 语音触发说话状态时需要；仅做桌宠展示可不使用' },
  { name: '角色素材', desc: '透明背景的 PNG 或 GIF 图片：至少准备闭嘴、张嘴两版，进阶可加眨眼、表情等分层' },
  { name: 'PNGTube Remix', desc: '免费开源的桌宠 / 直播软件（见第三节下载），用于制作和运行 .pngRemix 模型' },
  { name: '本站账号', desc: '注册一个账号即可上传、下载（开放授权的作品）、点赞与发布二创' },
]
</script>

<style scoped>
.tutorial-page {
  max-width: 860px;
  margin: 0 auto;
}
.lead {
  color: #606266;
}
.prepare-table {
  margin: 12px 0 20px;
}
.credit-alert {
  margin: 12px 0;
}
.credit-alert p {
  margin: 0;
  line-height: 2;
}
.code-block {
  background: #1f2937;
  color: #e5e7eb;
  padding: 16px;
  border-radius: 6px;
  font-family: monospace;
  line-height: 1.6;
  white-space: pre;
}
ol li {
  margin-bottom: 8px;
  line-height: 1.8;
}
ol ul {
  margin-top: 6px;
}
.alert-list {
  margin: 0;
  padding-left: 20px;
  line-height: 2;
}
.footnote {
  color: #909399;
  font-size: 13px;
}
code {
  background: #f0f2f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}
</style>
