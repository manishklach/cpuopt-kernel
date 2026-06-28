#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("CPUOpt-Kernel");
MODULE_DESCRIPTION("CPUOpt policy placeholder");

static int __init cpuopt_policy_init(void)
{
	pr_info("cpuopt_policy: placeholder module loaded\n");
	return 0;
}

static void __exit cpuopt_policy_exit(void)
{
	pr_info("cpuopt_policy: placeholder module unloaded\n");
}

module_init(cpuopt_policy_init);
module_exit(cpuopt_policy_exit);
