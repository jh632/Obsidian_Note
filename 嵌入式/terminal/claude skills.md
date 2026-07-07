## ponlytail Commands 

[github地址](https://github.com/DietrichGebert/ponytail#commands)

| Command  命令/指令                             | What it does  它的功能/作用是什么                               |
| ------------------------------------------ | ------------------------------------------------------ |
| `/ponytail [lite \| full \| ultra \| off]` | 可以调节强度，或者直接将其关闭。没有任何参数可以显示当前的强度水平。                     |
| `/ponytail-review`                         | 请检查当前的差异内容，看看是否存在过度设计的情况。之后把需要删除的内容列出来。                |
| `/ponytail-audit`                          | 要审核整个代码库中是否存在过度设计的情况，而不仅仅是查看代码的差异部分。                   |
| `/ponytail-debt`                           | 把那些你暂时搁置的 `ponytail:` 快捷方式记录下来吧，这样“稍后处理”就不会变成“永远不处理”了。 |
| `/ponytail-help`                           |   以上命令的快速参考。                                           |

这些指令需要由具备相应技能的主机来执行（比如 Claude Code、Codex、OpenCode、Gemini、pi 等）。在 Codex 中，这些指令被视作“技能”，可以通过 `@` （或 `@ponytail-review` ）来调用。而那些仅负责处理指令的适配器则无需这些指令，它们会直接加载预先设定的规则集来执行任务。
