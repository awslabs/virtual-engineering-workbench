export const REGULAR_EXPRESSIONS = {
  ssmParameter: /AWS::SSM::Parameter::Value<[<>:\w]+>/giu,
  securityGroupId: /AWS::EC2::SecurityGroup::Id/giu
};

export const MINUTES_PER_HOUR = 60;
export const HOURS_PER_DAY = 24;
export const MINUTES_PER_DAY = HOURS_PER_DAY * MINUTES_PER_HOUR;
export const LOWER_BOUND = 0;